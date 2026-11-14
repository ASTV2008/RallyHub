from __future__ import annotations

from app.domain import booking_rules as rules
from app.domain.csv_utils import to_csv
from app.domain.errors import (
    CancellationNotAllowed,
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    ReservationConflict,
    ResourceUnavailable,
)
from app.models import Facility, Reservation, User
from app.models.enums import ReservationStatus, Role, TableStatus
from app.repositories.facilities import TableRepository
from app.repositories.people import StudentRepository
from app.repositories.scheduling import ReservationRepository
from app.schemas.scheduling import ReservationCreate
from app.services.base import Service, require_roles


class ReservationService(Service):
    @property
    def repo(self) -> ReservationRepository:
        return ReservationRepository(self.db)

    # --- helpers de autorización --------------------------------------------------------------
    def _student_for_create(self, actor: User, data: ReservationCreate):
        students = StudentRepository(self.db)
        if actor.role == Role.STUDENT:
            me = students.by_user_id(actor.id)
            if me is None:
                raise ForbiddenError("Su usuario no tiene perfil de estudiante.")
            if data.student_id is not None and data.student_id != me.id:
                raise ForbiddenError("Solo puede reservar para sí mismo.")
            return me
        if actor.role == Role.ADMIN:
            if data.student_id is None:
                raise DomainError("Indique el estudiante (student_id).")
            st = students.get(data.student_id)
            if st is None:
                raise NotFoundError("Estudiante no encontrado.")
            return st
        raise ForbiddenError("Su rol no puede crear reservas.")

    def _can_view(self, actor: User, res: Reservation) -> bool:
        if actor.role == Role.ADMIN:
            return True
        if actor.role == Role.STUDENT:
            return res.student.user_id == actor.id
        if actor.role == Role.COACH and actor.coach:
            return StudentRepository(self.db).coach_teaches(actor.coach.id, res.student_id)
        return False

    # --- casos de uso ------------------------------------------------------------------------
    def create(self, actor: User, data: ReservationCreate) -> Reservation:
        student = self._student_for_create(actor, data)
        if not student.is_active:
            raise ResourceUnavailable("El estudiante está inactivo.")
        # 1) validaciones puras (sin tocar la BD)
        rules.validate_booking_window(self.policy, data.starts_at, data.ends_at, self.now())

        # 2) sección crítica: la transacción ya está abierta; bloqueamos la fila de la mesa.
        #    Cualquier otra reserva de la misma mesa espera aquí hasta nuestro COMMIT/ROLLBACK.
        tables = TableRepository(self.db)
        table = tables.get_for_update(data.table_id)
        if table is None:
            raise NotFoundError("Mesa no encontrada.")
        facility = self.db.get(Facility, table.facility_id)
        if table.status != TableStatus.ACTIVE or facility is None or not facility.is_active:
            raise ResourceUnavailable("La mesa no está disponible para reservas.")

        # 3) mantenimiento, clases y reservas activas que se solapan:
        #    existing_start < new_end AND existing_end > new_start (READ COMMITTED: ve lo último)
        kinds = {k for _, k, _, _ in tables.busy_slots([table.id], data.starts_at, data.ends_at)}
        if "MAINTENANCE" in kinds:
            raise ResourceUnavailable("La mesa tiene mantenimiento programado en ese horario.")
        if kinds:
            raise ReservationConflict("La mesa ya está ocupada en ese horario.")

        res = Reservation(student_id=student.id, table_id=table.id, starts_at=data.starts_at,
                          ends_at=data.ends_at, status=ReservationStatus.CONFIRMED,
                          notes=data.notes, created_by=actor.id)
        self.repo.add(res)
        if actor.role == Role.ADMIN:
            self.audit(actor, "CREATE", "reservation", res.id, f"student={student.id}")
        self.db.commit()  # libera el bloqueo
        return self.repo.get_full(res.id)  # type: ignore[return-value]

    def get(self, actor: User, reservation_id: int) -> Reservation:
        res = self.repo.get_full(reservation_id)
        if res is None:
            raise NotFoundError("Reserva no encontrada.")
        if not self._can_view(actor, res):
            raise ForbiddenError("No tiene permiso para ver esta reserva.")
        return res

    def search(self, actor: User, **filters):
        if actor.role == Role.ADMIN:
            return self.repo.search(**filters)
        if actor.role == Role.STUDENT:
            me = StudentRepository(self.db).by_user_id(actor.id)
            if me is None:
                raise ForbiddenError("Su usuario no tiene perfil de estudiante.")
            filters["student_id"] = me.id
            return self.repo.search(**filters)
        if actor.role == Role.COACH and actor.coach:
            filters["coach_id"] = actor.coach.id
            return self.repo.search(**filters)
        raise ForbiddenError("No tiene permiso para listar reservas.")

    def cancel(self, actor: User, reservation_id: int) -> Reservation:
        res = self.repo.get_for_update(reservation_id)
        if res is None:
            raise NotFoundError("Reserva no encontrada.")
        if actor.role == Role.STUDENT:
            me = StudentRepository(self.db).by_user_id(actor.id)
            if me is None or me.id != res.student_id:
                raise ForbiddenError("Solo puede cancelar sus propias reservas.")
        elif actor.role != Role.ADMIN:
            raise ForbiddenError("Su rol no puede cancelar reservas.")
        if res.status != ReservationStatus.CONFIRMED:
            raise ConflictError("Solo se pueden cancelar reservas confirmadas.")
        now = self.now()
        if actor.role == Role.STUDENT and not rules.can_student_cancel(
                self.policy, res.starts_at, now):
            raise CancellationNotAllowed(
                f"Solo puede cancelar hasta {self.policy.cancel_min_hours} horas antes del inicio.")
        res.status = ReservationStatus.CANCELLED
        res.cancelled_at = now
        if actor.role == Role.ADMIN:
            self.audit(actor, "CANCEL", "reservation", res.id)
        self.db.commit()
        return self.repo.get_full(reservation_id)  # type: ignore[return-value]

    def set_outcome(self, actor: User, reservation_id: int, status: ReservationStatus
                    ) -> Reservation:
        """ADMIN marca COMPLETED o NO_SHOW una reserva confirmada que ya comenzó."""
        require_roles(actor, Role.ADMIN)
        if status not in (ReservationStatus.COMPLETED, ReservationStatus.NO_SHOW):
            raise DomainError("Solo se permite COMPLETED o NO_SHOW (use cancelar para CANCELLED).")
        res = self.repo.get_for_update(reservation_id)
        if res is None:
            raise NotFoundError("Reserva no encontrada.")
        if res.status != ReservationStatus.CONFIRMED:
            raise ConflictError("Solo se puede cerrar una reserva confirmada.")
        if res.starts_at > self.now():
            raise ConflictError("La reserva aún no ha comenzado.")
        res.status = status
        self.audit(actor, status.value, "reservation", res.id)
        self.db.commit()
        return self.repo.get_full(reservation_id)  # type: ignore[return-value]

    def export_csv(self, actor: User, **filters) -> str:
        require_roles(actor, Role.ADMIN)
        items, _ = self.repo.search(limit=5000, offset=0, **filters)
        rows = [(r.id, r.student_name, r.facility_name, r.table_code,
                 r.starts_at.astimezone(self.settings.tz).isoformat(timespec="minutes"),
                 r.ends_at.astimezone(self.settings.tz).isoformat(timespec="minutes"),
                 r.status.value, r.notes or "") for r in items]
        return to_csv(["id", "estudiante", "instalacion", "mesa", "inicio", "fin", "estado",
                       "observacion"], rows)
