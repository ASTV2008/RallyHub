from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app.domain import booking_rules as rules
from app.domain.errors import (
    CancellationNotAllowed,
    CapacityExceeded,
    ConflictError,
    DomainError,
    DuplicateError,
    ForbiddenError,
    NotFoundError,
    PastDateError,
    ReservationConflict,
    ResourceUnavailable,
)
from app.models import Attendance, ClassEnrollment, ClassSession, Facility, User
from app.models.enums import ClassStatus, EnrollmentStatus, Role, TableStatus
from app.repositories.facilities import TableRepository
from app.repositories.people import StudentRepository
from app.repositories.scheduling import (
    AttendanceRepository,
    ClassRepository,
    EnrollmentRepository,
)
from app.schemas.scheduling import (
    AttendanceCreate,
    AttendanceUpdate,
    ClassCreate,
    ClassRead,
    ClassUpdate,
    EnrollmentCreate,
)
from app.services.base import Service


def _own_coach_id(actor: User) -> int:
    if actor.coach is None:
        raise ForbiddenError("Su usuario no tiene perfil de entrenador.")
    return actor.coach.id


def _own_student(actor: User, db):
    st = StudentRepository(db).by_user_id(actor.id)
    if st is None:
        raise ForbiddenError("Su usuario no tiene perfil de estudiante.")
    return st


class ClassService(Service):
    @property
    def repo(self) -> ClassRepository:
        return ClassRepository(self.db)

    def to_reads(self, classes: list[ClassSession]) -> list[ClassRead]:
        counts = self.repo.enrolled_counts([c.id for c in classes])
        return [ClassRead.model_validate(c).model_copy(update={"enrolled_count": counts.get(c.id, 0)})
                for c in classes]

    def _can_manage(self, actor: User, cls: ClassSession) -> bool:
        return actor.role == Role.ADMIN or (
            actor.role == Role.COACH and actor.coach is not None and cls.coach_id == actor.coach.id)

    def _check_resources(self, coach_id: int, table_id: int | None, start: datetime,
                         end: datetime, exclude_id: int | None) -> None:
        """Debe llamarse con los bloqueos ya tomados (orden: entrenador → mesa)."""
        if table_id is not None:
            tables = TableRepository(self.db)
            kinds = {k for _, k, _, _ in tables.busy_slots([table_id], start, end,
                                                          exclude_class_id=exclude_id)}
            if "MAINTENANCE" in kinds:
                raise ResourceUnavailable("La mesa tiene mantenimiento en ese horario.")
            if kinds:
                raise ReservationConflict("La mesa ya está ocupada (reserva o clase) en ese horario.")
        if self.repo.coach_has_conflict(coach_id, start, end, exclude_id):
            raise ConflictError("El entrenador ya tiene otra clase en ese horario.")

    def _lock_table_if_needed(self, table_id: int | None) -> None:
        if table_id is None:
            return
        table = TableRepository(self.db).get_for_update(table_id)
        if table is None:
            raise NotFoundError("Mesa no encontrada.")
        fac = self.db.get(Facility, table.facility_id)
        if table.status != TableStatus.ACTIVE or fac is None or not fac.is_active:
            raise ResourceUnavailable("La mesa no está disponible.")

    def create(self, actor: User, data: ClassCreate) -> ClassRead:
        if actor.role == Role.COACH:
            coach_id = _own_coach_id(actor)
            if data.coach_id not in (None, coach_id):
                raise ForbiddenError("Solo puede crear clases propias.")
        elif actor.role == Role.ADMIN:
            if data.coach_id is None:
                raise DomainError("Indique el entrenador (coach_id).")
            coach_id = data.coach_id
        else:
            raise ForbiddenError("Su rol no puede crear clases.")
        rules.validate_class_window(self.policy, data.starts_at, data.ends_at, self.now())

        coach = self.repo.lock_coach(coach_id)  # bloqueo 1: entrenador
        if coach is None:
            raise NotFoundError("Entrenador no encontrado.")
        if not coach.is_active:
            raise ResourceUnavailable("El entrenador está inactivo.")
        self._lock_table_if_needed(data.table_id)  # bloqueo 2: mesa
        self._check_resources(coach_id, data.table_id, data.starts_at, data.ends_at, None)

        cls = ClassSession(name=data.name, description=data.description, coach_id=coach_id,
                           table_id=data.table_id, level=data.level, capacity=data.capacity,
                           starts_at=data.starts_at, ends_at=data.ends_at,
                           status=ClassStatus.DRAFT)
        self.repo.add(cls)
        self.audit(actor, "CREATE", "class", cls.id)
        self.db.commit()
        return self.to_reads([self.repo.get_full(cls.id)])[0]  # type: ignore[list-item]

    def get(self, actor: User, class_id: int) -> ClassRead:
        cls = self.repo.get_full(class_id)
        if cls is None:
            raise NotFoundError("Clase no encontrada.")
        if actor.role != Role.ADMIN and not self._can_manage(actor, cls) \
                and cls.status != ClassStatus.PUBLISHED:
            raise ForbiddenError("No tiene permiso para ver esta clase.")
        return self.to_reads([cls])[0]

    def search(self, actor: User, *, status, level, date_from, date_to, sort_by, order,
               limit, offset) -> tuple[list[ClassRead], int]:
        coach_id = None
        if actor.role == Role.COACH:
            coach_id = _own_coach_id(actor)
        elif actor.role == Role.STUDENT:
            status = ClassStatus.PUBLISHED  # el estudiante solo ve clases publicadas
            date_from = max(date_from, self.now()) if date_from else self.now()
        items, total = self.repo.search(coach_id=coach_id, status=status, level=level,
                                        date_from=date_from, date_to=date_to, sort_by=sort_by,
                                        order=order, limit=limit, offset=offset)
        return self.to_reads(items), total

    def update(self, actor: User, class_id: int, data: ClassUpdate) -> ClassRead:
        cls = self.repo.get_full(class_id)
        if cls is None:
            raise NotFoundError("Clase no encontrada.")
        if not self._can_manage(actor, cls):
            raise ForbiddenError("No tiene permiso para modificar esta clase.")
        fields = data.model_dump(exclude_unset=True)
        clear_table = fields.pop("clear_table", False)
        coach_id = cls.coach_id
        self.repo.lock_coach(coach_id)  # bloqueo 1
        new_table = None if clear_table else fields.get("table_id", cls.table_id)
        for tid in sorted({t for t in (cls.table_id, new_table) if t is not None}):
            self._lock_table_if_needed(tid)  # bloqueo 2 (ids ordenados)
        locked = self.repo.get_for_update(class_id)  # bloqueo 3: la propia clase
        assert locked is not None
        if locked.status == ClassStatus.CANCELLED:
            raise ConflictError("No se puede modificar una clase cancelada.")
        if locked.starts_at <= self.now():
            raise PastDateError("La clase ya inició o finalizó y no puede modificarse.")
        start = fields.get("starts_at", locked.starts_at)
        end = fields.get("ends_at", locked.ends_at)
        capacity = fields.get("capacity", locked.capacity)
        rules.validate_class_window(self.policy, start, end, self.now())
        if capacity < self.repo.enrolled_count(class_id):
            raise CapacityExceeded("La capacidad no puede ser menor que los inscritos actuales.")
        self._check_resources(coach_id, new_table, start, end, class_id)
        for k, v in fields.items():
            if v is None and k in {"name", "level", "capacity", "starts_at", "ends_at"}:
                continue
            setattr(locked, k, v)
        locked.table_id = new_table
        self.audit(actor, "UPDATE", "class", class_id, ",".join(sorted(fields)))
        self.db.commit()
        return self.to_reads([self.repo.get_full(class_id)])[0]  # type: ignore[list-item]

    def set_status(self, actor: User, class_id: int, new: ClassStatus) -> ClassRead:
        cls = self.repo.get_for_update(class_id)
        if cls is None:
            raise NotFoundError("Clase no encontrada.")
        if not self._can_manage(actor, cls):
            raise ForbiddenError("No tiene permiso para modificar esta clase.")
        old = cls.status
        if old == ClassStatus.CANCELLED:
            raise ConflictError("La clase ya está cancelada.")
        if new == ClassStatus.PUBLISHED:
            if old != ClassStatus.DRAFT:
                raise ConflictError("Solo se puede publicar una clase en borrador.")
            if cls.starts_at <= self.now():
                raise PastDateError("No se puede publicar una clase que ya inició.")
        elif new == ClassStatus.DRAFT:
            if old != ClassStatus.PUBLISHED or self.repo.enrolled_count(class_id) > 0:
                raise ConflictError("Solo se oculta una clase publicada sin inscritos.")
        cls.status = new
        self.audit(actor, f"STATUS_{new.value}", "class", class_id, f"from={old.value}")
        self.db.commit()
        return self.to_reads([self.repo.get_full(class_id)])[0]  # type: ignore[list-item]


class EnrollmentService(Service):
    @property
    def repo(self) -> EnrollmentRepository:
        return EnrollmentRepository(self.db)

    def enroll(self, actor: User, data: EnrollmentCreate) -> ClassEnrollment:
        if actor.role == Role.STUDENT:
            student = _own_student(actor, self.db)
            if data.student_id not in (None, student.id):
                raise ForbiddenError("Solo puede inscribirse usted mismo.")
        elif actor.role == Role.ADMIN:
            if data.student_id is None:
                raise DomainError("Indique el estudiante (student_id).")
            student = StudentRepository(self.db).get(data.student_id)
            if student is None:
                raise NotFoundError("Estudiante no encontrado.")
        else:
            raise ForbiddenError("Su rol no puede inscribir estudiantes.")
        if not student.is_active:
            raise ResourceUnavailable("El estudiante está inactivo.")

        # Bloqueo de la fila de la clase: serializa inscripciones y protege el cupo.
        cls = ClassRepository(self.db).get_for_update(data.class_id)
        if cls is None:
            raise NotFoundError("Clase no encontrada.")
        if cls.status != ClassStatus.PUBLISHED:
            raise ResourceUnavailable("La clase no está disponible para inscripción.")
        if cls.starts_at <= self.now():
            raise PastDateError("La clase ya inició.")
        existing = self.repo.find(cls.id, student.id)
        if existing and existing.status == EnrollmentStatus.ENROLLED:
            raise DuplicateError("El estudiante ya está inscrito en esta clase.")
        if ClassRepository(self.db).enrolled_count(cls.id) >= cls.capacity:
            raise CapacityExceeded("La clase no tiene cupos disponibles.")
        try:
            if existing:  # reinscripción tras un retiro
                existing.status = EnrollmentStatus.ENROLLED
                existing.enrolled_at = self.now()
                enr = existing
            else:
                enr = self.repo.add(ClassEnrollment(class_id=cls.id, student_id=student.id,
                                                    status=EnrollmentStatus.ENROLLED,
                                                    enrolled_at=self.now()))
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateError("El estudiante ya está inscrito en esta clase.") from exc
        return self.repo.get_full(enr.id)  # type: ignore[return-value]

    def withdraw(self, actor: User, enrollment_id: int) -> None:
        enr = self.repo.get_full(enrollment_id)
        if enr is None:
            raise NotFoundError("Inscripción no encontrada.")
        if actor.role == Role.STUDENT:
            if enr.student.user_id != actor.id:
                raise ForbiddenError("Solo puede retirar sus propias inscripciones.")
            if enr.session.starts_at <= self.now():
                raise CancellationNotAllowed("La clase ya inició; no puede retirarse.")
        elif actor.role != Role.ADMIN:
            raise ForbiddenError("Su rol no puede retirar inscripciones.")
        if enr.status != EnrollmentStatus.ENROLLED:
            raise ConflictError("La inscripción ya fue retirada.")
        if AttendanceRepository(self.db).by_enrollment(enr.id):
            raise ConflictError("Ya existe asistencia registrada; no se puede retirar.")
        enr.status = EnrollmentStatus.WITHDRAWN
        if actor.role == Role.ADMIN:
            self.audit(actor, "WITHDRAW", "enrollment", enr.id)
        self.db.commit()

    def search(self, actor: User, *, class_id, student_id, status, limit, offset):
        if actor.role == Role.STUDENT:
            student_id = _own_student(actor, self.db).id
        elif actor.role == Role.COACH:
            if class_id is None:
                raise DomainError("Indique class_id.")
            cls = ClassRepository(self.db).get(class_id)
            if cls is None or cls.coach_id != _own_coach_id(actor):
                raise ForbiddenError("Solo puede ver inscripciones de sus clases.")
        return self.repo.search(class_id=class_id, student_id=student_id, status=status,
                                limit=limit, offset=offset)


class AttendanceService(Service):
    @property
    def repo(self) -> AttendanceRepository:
        return AttendanceRepository(self.db)

    def _authorize_class(self, actor: User, cls: ClassSession) -> None:
        if actor.role == Role.ADMIN:
            return
        if actor.role == Role.COACH and cls.coach_id == _own_coach_id(actor):
            return
        raise ForbiddenError("Solo el entrenador de la clase o un administrador puede registrar "
                             "asistencia.")

    def record(self, actor: User, data: AttendanceCreate) -> Attendance:
        enr = EnrollmentRepository(self.db).get_full(data.enrollment_id)
        if enr is None:
            raise NotFoundError("Inscripción no encontrada.")
        cls = enr.session
        self._authorize_class(actor, cls)
        if enr.status != EnrollmentStatus.ENROLLED:
            raise ConflictError("La inscripción no está activa.")
        if cls.status == ClassStatus.CANCELLED:
            raise ConflictError("La clase está cancelada.")
        if cls.starts_at > self.now():
            raise ConflictError("La clase aún no ha comenzado.")
        if self.repo.by_enrollment(enr.id):
            raise DuplicateError("Ya existe asistencia para este estudiante en la clase; "
                                 "utilice la corrección.")
        try:
            att = self.repo.add(Attendance(enrollment_id=enr.id, status=data.status,
                                           notes=data.notes, recorded_by=actor.id,
                                           recorded_at=self.now()))
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateError("Ya existe asistencia para este estudiante en la clase.") from exc
        return self.repo.get_full(att.id)  # type: ignore[return-value]

    def update(self, actor: User, attendance_id: int, data: AttendanceUpdate) -> Attendance:
        att = self.repo.get_full(attendance_id)
        if att is None:
            raise NotFoundError("Asistencia no encontrada.")
        self._authorize_class(actor, att.enrollment.session)
        fields = data.model_dump(exclude_unset=True)
        if fields.get("status") is not None:
            att.status = fields["status"]
        if "notes" in fields:
            att.notes = fields["notes"]
        att.updated_at = self.now()
        att.recorded_by = actor.id
        self.audit(actor, "UPDATE", "attendance", att.id)
        self.db.commit()
        return self.repo.get_full(attendance_id)  # type: ignore[return-value]

    def search(self, actor: User, *, class_id, student_id, limit, offset):
        if actor.role == Role.STUDENT:
            student_id = _own_student(actor, self.db).id
        elif actor.role == Role.COACH:
            if class_id is None:
                raise DomainError("Indique class_id.")
            cls = ClassRepository(self.db).get(class_id)
            if cls is None or cls.coach_id != _own_coach_id(actor):
                raise ForbiddenError("Solo puede ver asistencia de sus clases.")
        elif actor.role != Role.ADMIN:
            raise ForbiddenError("No tiene permiso.")
        return self.repo.search(class_id=class_id, student_id=student_id, limit=limit,
                                offset=offset)

