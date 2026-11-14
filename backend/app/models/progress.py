from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._common import created_at_col

SKILLS = ("serve", "receive", "ball_control", "movement", "strategy")


class ProgressRecord(Base):
    """Observación pedagógica del entrenador (escala 1–5). No es una medición oficial."""

    __tablename__ = "progress_records"
    __table_args__ = (
        *(CheckConstraint(f"{s} BETWEEN 1 AND 5", name=s) for s in SKILLS),
        Index("ix_progress_records_student_date", "student_id", "recorded_on"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    coach_id: Mapped[int] = mapped_column(ForeignKey("coaches.id"), nullable=False)
    recorded_on: Mapped[date] = mapped_column(Date, nullable=False)
    serve: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    receive: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ball_control: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    movement: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    strategy: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = created_at_col()
