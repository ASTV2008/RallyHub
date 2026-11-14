from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import contains_eager, joinedload

from app.models import ClassEnrollment, ClassSession, Coach, Student, User
from app.models.enums import EnrollmentStatus, Level
from app.repositories.base import BaseRepository, apply_sort, like_pattern


class UserRepository(BaseRepository[User]):
    model = User

    def by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))


class StudentRepository(BaseRepository[Student]):
    model = Student

    SORTABLE = {
        "last_name": Student.last_name,
        "first_name": Student.first_name,
        "level": Student.level,
        "created_at": Student.created_at,
    }

    def get_full(self, student_id: int) -> Student | None:
        return self.db.scalar(
            select(Student).options(joinedload(Student.user)).where(Student.id == student_id)
        )

    def by_user_id(self, user_id: int) -> Student | None:
        return self.db.scalar(select(Student).where(Student.user_id == user_id))

    def coach_teaches(self, coach_id: int, student_id: int) -> bool:
        """¿El estudiante está inscrito (activo) en alguna clase del entrenador?"""
        stmt = (
            select(ClassEnrollment.id)
            .join(ClassSession, ClassSession.id == ClassEnrollment.class_id)
            .where(
                ClassSession.coach_id == coach_id,
                ClassEnrollment.student_id == student_id,
                ClassEnrollment.status == EnrollmentStatus.ENROLLED,
            )
            .limit(1)
        )
        return self.db.scalar(stmt) is not None

    def search(self, *, q: str | None, level: Level | None, is_active: bool | None,
               coach_id: int | None, sort_by: str | None, order: str, limit: int, offset: int):
        stmt = select(Student).join(Student.user).options(contains_eager(Student.user))
        if q:
            pat = like_pattern(q)
            stmt = stmt.where(or_(Student.first_name.ilike(pat, escape="\\"),
                                  Student.last_name.ilike(pat, escape="\\"),
                                  User.email.ilike(pat, escape="\\")))
        if level:
            stmt = stmt.where(Student.level == level)
        if is_active is not None:
            stmt = stmt.where(Student.is_active == is_active)
        if coach_id is not None:
            sub = (
                select(ClassEnrollment.student_id)
                .join(ClassSession, ClassSession.id == ClassEnrollment.class_id)
                .where(ClassSession.coach_id == coach_id,
                       ClassEnrollment.status == EnrollmentStatus.ENROLLED)
            )
            stmt = stmt.where(Student.id.in_(sub))
        stmt = apply_sort(stmt, self.SORTABLE, sort_by, order, "last_name", Student.id)
        return self.paginate(stmt, limit, offset)


class CoachRepository(BaseRepository[Coach]):
    model = Coach

    SORTABLE = {
        "last_name": Coach.last_name,
        "first_name": Coach.first_name,
        "created_at": Coach.created_at,
    }

    def get_full(self, coach_id: int) -> Coach | None:
        return self.db.scalar(
            select(Coach).options(joinedload(Coach.user)).where(Coach.id == coach_id)
        )

    def by_user_id(self, user_id: int) -> Coach | None:
        return self.db.scalar(select(Coach).where(Coach.user_id == user_id))

    def search(self, *, q: str | None, is_active: bool | None, sort_by: str | None, order: str,
               limit: int, offset: int):
        stmt = select(Coach).join(Coach.user).options(contains_eager(Coach.user))
        if q:
            pat = like_pattern(q)
            stmt = stmt.where(or_(Coach.first_name.ilike(pat, escape="\\"),
                                  Coach.last_name.ilike(pat, escape="\\"),
                                  Coach.specialty.ilike(pat, escape="\\")))
        if is_active is not None:
            stmt = stmt.where(Coach.is_active == is_active)
        stmt = apply_sort(stmt, self.SORTABLE, sort_by, order, "last_name", Coach.id)
        return self.paginate(stmt, limit, offset)
