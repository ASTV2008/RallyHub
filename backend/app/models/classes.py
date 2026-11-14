from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UTCDateTime
from app.models._common import created_at_col, enum_col
from app.models.enums import AttendanceStatus, ClassStatus, EnrollmentStatus, Level
from app.models.facilities import GameTable
from app.models.users import Coach, Student


class ClassSession(Base):
    """Clase = sesión única con fecha/hora explícitas (sin recurrencia en el MVP)."""

    __tablename__ = "classes"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="range"),
        CheckConstraint("capacity >= 1", name="capacity"),
        Index("ix_classes_coach_range", "coach_id", "starts_at", "ends_at"),
        Index("ix_classes_table_range", "table_id", "starts_at", "ends_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    coach_id: Mapped[int] = mapped_column(ForeignKey("coaches.id"), nullable=False)
    table_id: Mapped[int | None] = mapped_column(ForeignKey("tables.id"))
    level: Mapped[Level] = mapped_column(enum_col(Level, "class_level"), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    status: Mapped[ClassStatus] = mapped_column(
        enum_col(ClassStatus, "class_status"), nullable=False, default=ClassStatus.DRAFT
    )
    created_at: Mapped[datetime] = created_at_col()

    coach: Mapped[Coach] = relationship()
    table: Mapped[GameTable | None] = relationship()

    @property
    def coach_name(self) -> str:
        return self.coach.full_name

    @property
    def table_code(self) -> str | None:
        return self.table.code if self.table else None


class ClassEnrollment(Base):
    __tablename__ = "class_enrollments"
    __table_args__ = (UniqueConstraint("class_id", "student_id", name="uq_class_enrollments_class_student"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False,
                                            index=True)
    status: Mapped[EnrollmentStatus] = mapped_column(
        enum_col(EnrollmentStatus, "enrollment_status"),
        nullable=False,
        default=EnrollmentStatus.ENROLLED,
    )
    enrolled_at: Mapped[datetime] = created_at_col()

    session: Mapped[ClassSession] = relationship()
    student: Mapped[Student] = relationship()

    @property
    def student_name(self) -> str:
        return self.student.full_name

    @property
    def class_name(self) -> str:
        return self.session.name

    @property
    def class_starts_at(self) -> datetime:
        return self.session.starts_at


class Attendance(Base):
    """Una asistencia por inscripción (la clase es una única sesión)."""

    __tablename__ = "attendances"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("class_enrollments.id"), unique=True, nullable=False
    )
    status: Mapped[AttendanceStatus] = mapped_column(
        enum_col(AttendanceStatus, "attendance_status"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(String(300))
    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    recorded_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    enrollment: Mapped[ClassEnrollment] = relationship()

    @property
    def class_id(self) -> int:
        return self.enrollment.class_id

    @property
    def student_id(self) -> int:
        return self.enrollment.student_id

    @property
    def student_name(self) -> str:
        return self.enrollment.student.full_name
