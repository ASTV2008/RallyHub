from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from app.domain.booking_rules import validate_interval
from app.domain.errors import (
    DuplicateError,
    FutureReservationsExist,
    InvalidInterval,
    NotFoundError,
    PastDateError,
    ResourceUnavailable,
)
from app.models import Facility, GameTable, MaintenanceBlock, User
from app.models.enums import ReservationStatus, Role, TableStatus
from app.repositories.facilities import FacilityRepository, TableRepository
from app.schemas.facilities import (
    BusySlot,
    FacilityCreate,
    FacilityUpdate,
    MaintenanceCreate,
    TableAvailability,
    TableCreate,
    TableUpdate,
)
from app.services.base import Service, require_roles

MAX_AVAILABILITY_SPAN = timedelta(days=7)
_STATUS_REASON = {
    TableStatus.MAINTENANCE: "Mesa en mantenimiento.",
    TableStatus.OUT_OF_SERVICE: "Mesa fuera de servicio.",
}


class _TableRelease(Service):
    """Lógica común: qué pasa con la agenda cuando una mesa (o toda una sede) deja de servir."""

    def _release_tables(self, actor: User, table_ids: list[int], *, cancel_reservations: bool,
                        subject: str) -> int:
        """Comprueba la agenda futura de `table_ids` y, si se pide, cancela las reservas.

        Las clases futuras bloquean siempre (deben reprogramarse). Las reservas confirmadas
        bloquean salvo `cancel_reservations=True`, en cuyo caso se cancelan y se auditan.
        Devuelve el número de reservas canceladas. No hace commit.
        """
        if not table_ids:
            return 0
        repo = TableRepository(self.db)
        now = self.now()
        classes = repo.future_classes(table_ids, now)
        if classes:
            raise ResourceUnavailable(
                f"{subject} tiene {len(classes)} clase(s) programada(s); "
                "reprográmelas o cancélelas antes de continuar.")
        pending = repo.future_confirmed_reservations(table_ids, now)
        if not pending:
            return 0
        if not cancel_reservations:
            raise FutureReservationsExist(
                f"{subject} tiene {len(pending)} reserva(s) confirmada(s) pendiente(s).")
        for res in pending:
            res.status = ReservationStatus.CANCELLED
            res.cancelled_at = now
            self.audit(actor, "CANCEL", "reservation", res.id, "auto: mesa no disponible")
        return len(pending)


class FacilityService(_TableRelease):
    @property
    def repo(self) -> FacilityRepository:
        return FacilityRepository(self.db)

    def _lock_tables(self, facility_id: int) -> list[int]:
        """Bloquea (en orden de id, sin interbloqueos) todas las mesas de la sede."""
        tables, _ = TableRepository(self.db).search(
            facility_id=facility_id, status=None, q=None, sort_by=None, order="asc",
            limit=500, offset=0)
        ids = sorted(t.id for t in tables)
        for tid in ids:
            TableRepository(self.db).get_for_update(tid)
        return ids

    def create(self, actor: User, data: FacilityCreate) -> Facility:
        require_roles(actor, Role.ADMIN)
        if self.repo.by_name(data.name):
            raise DuplicateError("Ya existe una instalación con ese nombre.")
        fac = Facility(**data.model_dump(), is_active=True)
        try:
            self.repo.add(fac)
            self.audit(actor, "CREATE", "facility", fac.id)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateError("Ya existe una instalación con ese nombre.") from exc
        return fac

    def get(self, facility_id: int) -> Facility:
        fac = self.repo.get(facility_id)
        if fac is None:
            raise NotFoundError("Instalación no encontrada.")
        return fac

    def update(self, actor: User, facility_id: int, data: FacilityUpdate, *,
               cancel_reservations: bool = False) -> Facility:
        require_roles(actor, Role.ADMIN)
        fac = self.get(facility_id)
        fields = data.model_dump(exclude_unset=True)
        if fields.get("is_active") is False and fac.is_active:
            self._release_tables(actor, self._lock_tables(fac.id),
                                 cancel_reservations=cancel_reservations,
                                 subject="La instalación")
        new_name = fields.get("name")
        if new_name and new_name != fac.name and self.repo.by_name(new_name):
            raise DuplicateError("Ya existe una instalación con ese nombre.")
        for k, v in fields.items():
            if v is None and k == "name":
                continue
            if v is None and k == "is_active":
                continue
            setattr(fac, k, v)
        self.audit(actor, "UPDATE", "facility", fac.id, ",".join(sorted(fields)))
        self.db.commit()
        return fac

    def deactivate(self, actor: User, facility_id: int, *, cancel_reservations: bool = False
                   ) -> None:
        require_roles(actor, Role.ADMIN)
        fac = self.get(facility_id)
        if fac.is_active:
            self._release_tables(actor, self._lock_tables(fac.id),
                                 cancel_reservations=cancel_reservations,
                                 subject="La instalación")
        fac.is_active = False
        self.audit(actor, "DEACTIVATE", "facility", fac.id)
        self.db.commit()


class TableService(_TableRelease):
    @property
    def repo(self) -> TableRepository:
        return TableRepository(self.db)

    def create(self, actor: User, data: TableCreate) -> GameTable:
        require_roles(actor, Role.ADMIN)
        if self.db.get(Facility, data.facility_id) is None:
            raise NotFoundError("Instalación no encontrada.")
        if self.repo.by_code(data.facility_id, data.code):
            raise DuplicateError("Ya existe una mesa con ese código en la instalación.")
        table = GameTable(**data.model_dump())
        try:
            self.repo.add(table)
            self.audit(actor, "CREATE", "table", table.id)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateError("Ya existe una mesa con ese código en la instalación.") from exc
        return self.get(table.id)

    def get(self, table_id: int) -> GameTable:
        table = self.repo.get_full(table_id)
        if table is None:
            raise NotFoundError("Mesa no encontrada.")
        return table

    def update(self, actor: User, table_id: int, data: TableUpdate, *,
               cancel_reservations: bool = False) -> GameTable:
        require_roles(actor, Role.ADMIN)
        if self.repo.get_for_update(table_id) is None:  # serializa contra reservas de la mesa
            raise NotFoundError("Mesa no encontrada.")
        table = self.get(table_id)
        fields = data.model_dump(exclude_unset=True)
        if fields.get("status") not in (None, TableStatus.ACTIVE):
            self._release_tables(actor, [table.id], cancel_reservations=cancel_reservations,
                                 subject="La mesa")
        code = fields.get("code")
        if code and code != table.code and self.repo.by_code(table.facility_id, code):
            raise DuplicateError("Ya existe una mesa con ese código en la instalación.")
        for k, v in fields.items():
            if v is None and k in {"code", "status"}:
                continue
            setattr(table, k, v)
        self.audit(actor, "UPDATE", "table", table.id, ",".join(sorted(fields)))
        self.db.commit()
        return self.get(table_id)

    def retire(self, actor: User, table_id: int, *, cancel_reservations: bool = False) -> None:
        """Baja lógica: la mesa queda OUT_OF_SERVICE y conserva su historial."""
        require_roles(actor, Role.ADMIN)
        if self.repo.get_for_update(table_id) is None:
            raise NotFoundError("Mesa no encontrada.")
        table = self.get(table_id)
        self._release_tables(actor, [table.id], cancel_reservations=cancel_reservations,
                             subject="La mesa")
        table.status = TableStatus.OUT_OF_SERVICE
        self.audit(actor, "RETIRE", "table", table.id)
        self.db.commit()

    # --- disponibilidad (calculada desde la base de datos) ------------------------------------
    def availability(self, start: datetime, end: datetime, *, facility_id: int | None = None,
                     table_id: int | None = None) -> list[TableAvailability]:
        validate_interval(start, end)
        if end - start > MAX_AVAILABILITY_SPAN:
            raise InvalidInterval("El rango de consulta no puede superar 7 días.")
        if table_id is not None:
            tables = [self.get(table_id)]
        else:
            tables, _ = self.repo.search(facility_id=facility_id, status=None, q=None,
                                        sort_by=None, order="asc", limit=500, offset=0)
        slots = self.repo.busy_slots([t.id for t in tables], start, end)
        by_table: dict[int, list[BusySlot]] = defaultdict(list)
        for tid, kind, s, e in slots:
            by_table[tid].append(BusySlot(kind=kind, starts_at=s, ends_at=e))
        out = []
        for t in tables:
            busy = sorted(by_table.get(t.id, []), key=lambda b: b.starts_at)
            reason = None
            if not t.facility.is_active:
                reason = "Instalación inactiva."
            elif t.status != TableStatus.ACTIVE:
                reason = _STATUS_REASON[t.status]
            elif busy:
                reason = "Ocupada en el horario solicitado."
            out.append(TableAvailability(
                table_id=t.id, code=t.code, facility_id=t.facility_id,
                facility_name=t.facility.name, status=t.status, available=reason is None,
                reason=reason, busy=busy))
        return out

    # --- mantenimiento -----------------------------------------------------------------------
    def add_maintenance(self, actor: User, table_id: int, data: MaintenanceCreate
                        ) -> MaintenanceBlock:
        require_roles(actor, Role.ADMIN)
        validate_interval(data.starts_at, data.ends_at)
        now = self.now()
        if data.ends_at <= now:
            raise PastDateError("El bloqueo de mantenimiento debe terminar en el futuro.")
        table = self.repo.get_for_update(table_id)  # serializa contra reservas de la mesa
        if table is None:
            raise NotFoundError("Mesa no encontrada.")
        kinds = {k for _, k, _, _ in self.repo.busy_slots([table_id], data.starts_at,
                                                         data.ends_at)}
        if "CLASS" in kinds:
            raise ResourceUnavailable(
                "Hay clases programadas en ese rango; reprográmelas o cancélelas antes de "
                "programar el mantenimiento.")
        overlapping = self.repo.reservations_overlapping([table_id], data.starts_at, data.ends_at)
        closed = [r for r in overlapping if r.status != ReservationStatus.CONFIRMED]
        if closed:
            raise ResourceUnavailable(
                "El rango incluye reservas ya completadas o marcadas como no asistidas; "
                "elija un rango que comience después.")
        if overlapping:
            if not data.cancel_conflicts:
                raise FutureReservationsExist(
                    f"Hay {len(overlapping)} reserva(s) confirmada(s) en ese rango.")
            for res in overlapping:
                res.status = ReservationStatus.CANCELLED
                res.cancelled_at = now
                self.audit(actor, "CANCEL", "reservation", res.id, "auto: mantenimiento")
        block = MaintenanceBlock(table_id=table_id, starts_at=data.starts_at, ends_at=data.ends_at,
                                 reason=data.reason, created_by=actor.id)
        self.db.add(block)
        self.db.flush()
        self.audit(actor, "CREATE", "maintenance_block", block.id, f"table={table_id}")
        self.db.commit()
        return block

    def list_maintenance(self, table_id: int) -> list[MaintenanceBlock]:
        self.get(table_id)
        return self.repo.maintenance_for(table_id)

    def remove_maintenance(self, actor: User, table_id: int, block_id: int) -> None:
        require_roles(actor, Role.ADMIN)
        block = self.db.get(MaintenanceBlock, block_id)
        if block is None or block.table_id != table_id:
            raise NotFoundError("Bloqueo de mantenimiento no encontrado.")
        self.db.delete(block)
        self.audit(actor, "DELETE", "maintenance_block", block_id)
        self.db.commit()
