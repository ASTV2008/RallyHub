from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.domain import stats
from app.domain.errors import ForbiddenError
from app.models import (
    Attendance,
    ClassEnrollment,
    ClassSession,
    Coach,
    GameTable,
    Reservation,
    Student,
    User,
)
from app.models.enums import (
    AttendanceStatus,
    ClassStatus,
    EnrollmentStatus,
    ReservationStatus,
    Role,
    TableStatus,
)
from app.repositories.people import StudentRepository
from app.repositories.scheduling import ClassRepository, ReservationRepository
from app.schemas.dashboard import (
    AdminDashboard,
    CoachDashboard,
    StudentDashboard,
    TableOccupancy,
)
from app.schemas.scheduling import ReservationRead
from app.services.base import Service
from app.services.classes import ClassService

OCCUPANCY_DAYS = 7
ATTENDANCE_DAYS = 30
_ACTIVE_RES = (ReservationStatus.CONFIRMED, ReservationStatus.COMPLETED)


class DashboardService(Service):
    def _attendance_counts(self, since, until, *, coach_id: int | None = None,
                           student_id: int | None = None) -> tuple[int, int]:
        stmt = (select(Attendance.status, func.count())
                .join(ClassEnrollment, ClassEnrollment.id == Attendance.enrollment_id)
                .join(ClassSession, ClassSession.id == ClassEnrollment.class_id)
                .where(ClassSession.starts_at >= since, ClassSession.starts_at < until))
        if coach_id is not None:
            stmt = stmt.where(ClassSession.coach_id == coach_id)
        if student_id is not None:
            stmt = stmt.where(ClassEnrollment.student_id == student_id)
        counts = {st: n for st, n in self.db.execute(stmt.group_by(Attendance.status))}
        return counts.get(AttendanceStatus.PRESENT, 0), counts.get(AttendanceStatus.ABSENT, 0)

    def _upcoming_classes(self, now, *, coach_id=None, student_id=None, limit=5):
        stmt = select(ClassSession.id).where(ClassSession.ends_at > now,
                                             ClassSession.status != ClassStatus.CANCELLED)
        if coach_id is not None:
            stmt = stmt.where(ClassSession.coach_id == coach_id)
        elif student_id is not None:
            stmt = stmt.where(ClassSession.status == ClassStatus.PUBLISHED, ClassSession.id.in_(
                select(ClassEnrollment.class_id).where(ClassEnrollment.student_id == student_id,
                                                       ClassEnrollment.status == EnrollmentStatus.ENROLLED)))
        else:
            stmt = stmt.where(ClassSession.status == ClassStatus.PUBLISHED)
        ids = list(self.db.scalars(stmt.order_by(ClassSession.starts_at).limit(limit)))
        repo = ClassRepository(self.db)
        classes = [c for i in ids if (c := repo.get_full(i))]
        return ClassService(self.db, self.settings, self.clock).to_reads(classes)

    def admin(self, actor: User) -> AdminDashboard:
        if actor.role != Role.ADMIN:
            raise ForbiddenError("Solo administración.")
        now = self.now()
        tz = self.settings.tz
        day0, day1 = stats.local_day_bounds(now, tz)
        wk0, wk1 = stats.local_week_bounds(now, tz)

        def count(model, *where) -> int:
            return int(self.db.scalar(select(func.count()).select_from(model).where(*where)) or 0)

        def res_between(a, b) -> int:
            return count(Reservation, Reservation.status.in_(_ACTIVE_RES),
                         Reservation.starts_at >= a, Reservation.starts_at < b)

        # Ocupación: últimos 7 días locales completos hasta hoy inclusive.
        win_end = day1
        win_start = day1 - timedelta(days=OCCUPANCY_DAYS)
        tables = list(self.db.scalars(select(GameTable).options(joinedload(GameTable.facility)).where(
            GameTable.status == TableStatus.ACTIVE).order_by(GameTable.code)))
        res_rows = self.db.execute(
            select(Reservation.table_id, Reservation.starts_at, Reservation.ends_at).where(
                Reservation.status.in_(_ACTIVE_RES), Reservation.starts_at < win_end,
                Reservation.ends_at > win_start)).all()
        class_rows = self.db.execute(
            select(ClassSession.table_id, ClassSession.starts_at, ClassSession.ends_at).where(
                ClassSession.table_id.is_not(None), ClassSession.status != ClassStatus.CANCELLED,
                ClassSession.starts_at < win_end, ClassSession.ends_at > win_start)).all()
        capacity = OCCUPANCY_DAYS * self.settings.open_minutes_per_day
        # Ocupación = minutos con reserva (CONFIRMED/COMPLETED) o clase no cancelada / minutos operativos.
        occ = stats.occupancy_by_table([(t, s, e) for t, s, e in [*res_rows, *class_rows]],
                                       [t.id for t in tables], win_start, win_end, capacity)
        fac_names = {t.id: t.facility.name for t in tables}
        present, absent = self._attendance_counts(now - timedelta(days=ATTENDANCE_DAYS), now)
        level_rows = self.db.scalars(select(Student.level).where(Student.is_active.is_(True)))
        return AdminDashboard(
            active_students=count(Student, Student.is_active.is_(True)),
            active_coaches=count(Coach, Coach.is_active.is_(True)),
            enabled_tables=len(tables),
            reservations_today=res_between(day0, day1),
            reservations_week=res_between(wk0, wk1),
            upcoming_classes=self._upcoming_classes(now),
            occupancy_period_days=OCCUPANCY_DAYS,
            occupancy_by_table=[TableOccupancy(table_id=t.id, code=t.code,
                                               facility_name=fac_names[t.id],
                                               occupancy_pct=occ[t.id]) for t in tables],
            attendance_period_days=ATTENDANCE_DAYS,
            attendance_rate_pct=stats.attendance_rate(present, absent),
            students_by_level=stats.count_by(lv.value for lv in level_rows),
            generated_at=now,
        )

    def coach(self, actor: User) -> CoachDashboard:
        if actor.role != Role.COACH or actor.coach is None:
            raise ForbiddenError("Solo entrenadores.")
        now = self.now()
        coach_id = actor.coach.id
        students = StudentRepository(self.db)
        _, total = students.search(q=None, level=None, is_active=True, coach_id=coach_id,
                                   sort_by=None, order="asc", limit=1, offset=0)
        present, absent = self._attendance_counts(now - timedelta(days=ATTENDANCE_DAYS), now,
                                                  coach_id=coach_id)
        return CoachDashboard(
            upcoming_classes=self._upcoming_classes(now, coach_id=coach_id),
            active_students=total, attendance_period_days=ATTENDANCE_DAYS,
            attendance_rate_pct=stats.attendance_rate(present, absent), generated_at=now)

    def student(self, actor: User) -> StudentDashboard:
        me = StudentRepository(self.db).by_user_id(actor.id) if actor.role == Role.STUDENT else None
        if me is None:
            raise ForbiddenError("Solo estudiantes.")
        now = self.now()
        items, _ = ReservationRepository(self.db).search(
            student_id=me.id, status=ReservationStatus.CONFIRMED, date_from=now, limit=5)
        present, absent = self._attendance_counts(now - timedelta(days=ATTENDANCE_DAYS), now,
                                                  student_id=me.id)
        return StudentDashboard(
            upcoming_reservations=[ReservationRead.model_validate(r) for r in items],
            upcoming_classes=self._upcoming_classes(now, student_id=me.id),
            attendance_period_days=ATTENDANCE_DAYS,
            attendance_rate_pct=stats.attendance_rate(present, absent), generated_at=now)
