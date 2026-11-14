from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, selectinload

from app.models import (
    Attendance,
    ClassEnrollment,
    ClassSession,
    Coach,
    GameTable,
    Reservation,
    Student,
)
from app.models.enums import ClassStatus, EnrollmentStatus, Level, ReservationStatus
from app.repositories.base import BaseRepository, apply_sort

_RES_LOAD = (joinedload(Reservation.student).joinedload(Student.user),
             joinedload(Reservation.table).joinedload(GameTable.facility))


class ReservationRepository(BaseRepository[Reservation]):
    model = Reservation

    SORTABLE = {"starts_at": Reservation.starts_at, "created_at": Reservation.created_at,
                "status": Reservation.status}

    def get_full(self, reservation_id: int) -> Reservation | None:
        return self.db.scalar(
            select(Reservation).options(*_RES_LOAD).where(Reservation.id == reservation_id)
        )

    def get_for_update(self, reservation_id: int) -> Reservation | None:
        return self.db.scalar(
            select(Reservation).where(Reservation.id == reservation_id).with_for_update()
        )

    def search(self, *, student_id: int | None = None, table_id: int | None = None,
               facility_id: int | None = None, status: ReservationStatus | None = None,
               date_from: datetime | None = None, date_to: datetime | None = None,
               coach_id: int | None = None, sort_by: str | None = None, order: str = "asc",
               limit: int = 50, offset: int = 0):
        stmt = select(Reservation).options(*_RES_LOAD)
        if student_id is not None:
            stmt = stmt.where(Reservation.student_id == student_id)
        if table_id is not None:
            stmt = stmt.where(Reservation.table_id == table_id)
        if facility_id is not None:
            stmt = stmt.where(Reservation.table_id.in_(
                select(GameTable.id).where(GameTable.facility_id == facility_id)))
        if status:
            stmt = stmt.where(Reservation.status == status)
        if date_from:
            stmt = stmt.where(Reservation.ends_at > date_from)
        if date_to:
            stmt = stmt.where(Reservation.starts_at < date_to)
        if coach_id is not None:  # reservas de estudiantes que cursan clases del entrenador
            sub = (select(ClassEnrollment.student_id)
                   .join(ClassSession, ClassSession.id == ClassEnrollment.class_id)
                   .where(ClassSession.coach_id == coach_id,
                          ClassEnrollment.status == EnrollmentStatus.ENROLLED))
            stmt = stmt.where(Reservation.student_id.in_(sub))
        stmt = apply_sort(stmt, self.SORTABLE, sort_by, order, "starts_at", Reservation.id)
        return self.paginate(stmt, limit, offset)


_CLS_LOAD = (joinedload(ClassSession.coach), joinedload(ClassSession.table))


class ClassRepository(BaseRepository[ClassSession]):
    model = ClassSession

    SORTABLE = {"starts_at": ClassSession.starts_at, "name": ClassSession.name,
                "level": ClassSession.level, "created_at": ClassSession.created_at}

    def get_full(self, class_id: int) -> ClassSession | None:
        return self.db.scalar(
            select(ClassSession).options(*_CLS_LOAD).where(ClassSession.id == class_id)
        )

    def get_for_update(self, class_id: int) -> ClassSession | None:
        return self.db.scalar(
            select(ClassSession).where(ClassSession.id == class_id).with_for_update()
        )

    def lock_coach(self, coach_id: int) -> Coach | None:
        """Serializa la creación de clases del mismo entrenador (orden de bloqueo: coach → mesa)."""
        return self.db.scalar(select(Coach).where(Coach.id == coach_id).with_for_update())

    def coach_has_conflict(self, coach_id: int, start: datetime, end: datetime,
                           exclude_id: int | None = None) -> bool:
        stmt = select(ClassSession.id).where(
            ClassSession.coach_id == coach_id,
            ClassSession.status != ClassStatus.CANCELLED,
            ClassSession.starts_at < end,
            ClassSession.ends_at > start,
        ).limit(1)
        if exclude_id is not None:
            stmt = stmt.where(ClassSession.id != exclude_id)
        return self.db.scalar(stmt) is not None

    def search(self, *, coach_id: int | None = None, status: ClassStatus | None = None,
               level: Level | None = None, date_from: datetime | None = None,
               date_to: datetime | None = None, sort_by: str | None = None, order: str = "asc",
               limit: int = 50, offset: int = 0):
        stmt = select(ClassSession).options(*_CLS_LOAD)
        if coach_id is not None:
            stmt = stmt.where(ClassSession.coach_id == coach_id)
        if status:
            stmt = stmt.where(ClassSession.status == status)
        if level:
            stmt = stmt.where(ClassSession.level == level)
        if date_from:
            stmt = stmt.where(ClassSession.ends_at > date_from)
        if date_to:
            stmt = stmt.where(ClassSession.starts_at < date_to)
        stmt = apply_sort(stmt, self.SORTABLE, sort_by, order, "starts_at", ClassSession.id)
        return self.paginate(stmt, limit, offset)

    def enrolled_counts(self, class_ids: list[int]) -> dict[int, int]:
        if not class_ids:
            return {}
        rows = self.db.execute(
            select(ClassEnrollment.class_id, func.count())
            .where(ClassEnrollment.class_id.in_(class_ids),
                   ClassEnrollment.status == EnrollmentStatus.ENROLLED)
            .group_by(ClassEnrollment.class_id)
        )
        return {cid: n for cid, n in rows}

    def enrolled_count(self, class_id: int) -> int:
        return self.enrolled_counts([class_id]).get(class_id, 0)


_ENR_LOAD = (joinedload(ClassEnrollment.session),
             joinedload(ClassEnrollment.student).joinedload(Student.user))


class EnrollmentRepository(BaseRepository[ClassEnrollment]):
    model = ClassEnrollment

    def get_full(self, enrollment_id: int) -> ClassEnrollment | None:
        return self.db.scalar(
            select(ClassEnrollment).options(*_ENR_LOAD).where(ClassEnrollment.id == enrollment_id)
        )

    def find(self, class_id: int, student_id: int) -> ClassEnrollment | None:
        return self.db.scalar(select(ClassEnrollment).where(
            ClassEnrollment.class_id == class_id, ClassEnrollment.student_id == student_id))

    def search(self, *, class_id: int | None, student_id: int | None,
               status: EnrollmentStatus | None, limit: int, offset: int):
        stmt = select(ClassEnrollment).options(*_ENR_LOAD)
        if class_id is not None:
            stmt = stmt.where(ClassEnrollment.class_id == class_id)
        if student_id is not None:
            stmt = stmt.where(ClassEnrollment.student_id == student_id)
        if status:
            stmt = stmt.where(ClassEnrollment.status == status)
        stmt = stmt.order_by(ClassEnrollment.id)
        return self.paginate(stmt, limit, offset)


class AttendanceRepository(BaseRepository[Attendance]):
    model = Attendance

    def _load(self):
        return (selectinload(Attendance.enrollment).joinedload(ClassEnrollment.student)
                .joinedload(Student.user),)

    def get_full(self, attendance_id: int) -> Attendance | None:
        return self.db.scalar(
            select(Attendance).options(*self._load()).where(Attendance.id == attendance_id)
        )

    def by_enrollment(self, enrollment_id: int) -> Attendance | None:
        return self.db.scalar(select(Attendance).where(Attendance.enrollment_id == enrollment_id))

    def search(self, *, class_id: int | None, student_id: int | None, limit: int, offset: int):
        stmt = select(Attendance).join(Attendance.enrollment).options(*self._load())
        if class_id is not None:
            stmt = stmt.where(ClassEnrollment.class_id == class_id)
        if student_id is not None:
            stmt = stmt.where(ClassEnrollment.student_id == student_id)
        stmt = stmt.order_by(Attendance.id)
        return self.paginate(stmt, limit, offset)
