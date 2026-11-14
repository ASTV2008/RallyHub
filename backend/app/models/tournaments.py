from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._common import created_at_col, enum_col
from app.models.enums import Modality, TournamentStatus
from app.models.users import Student


class Tournament(Base):
    __tablename__ = "tournaments"
    __table_args__ = (
        CheckConstraint("ends_on >= starts_on", name="range"),
        CheckConstraint("capacity >= 2", name="capacity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str | None] = mapped_column(String(60))
    modality: Mapped[Modality] = mapped_column(enum_col(Modality, "tournament_modality"),
                                               nullable=False, default=Modality.SINGLES)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    location: Mapped[str | None] = mapped_column(String(200))
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[TournamentStatus] = mapped_column(
        enum_col(TournamentStatus, "tournament_status"), nullable=False,
        default=TournamentStatus.OPEN,
    )
    created_at: Mapped[datetime] = created_at_col()


class TournamentParticipant(Base):
    __tablename__ = "tournament_participants"
    __table_args__ = (UniqueConstraint("tournament_id", "student_id", name="uq_tournament_participants_tournament_student"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), nullable=False,
                                               index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    registered_at: Mapped[datetime] = created_at_col()

    student: Mapped[Student] = relationship()

    @property
    def student_name(self) -> str:
        return self.student.full_name


class TournamentMatch(Base):
    """Resultado registrado manualmente. No hay generador de cuadros en el MVP."""

    __tablename__ = "tournament_matches"
    __table_args__ = (
        CheckConstraint("participant_a_id <> participant_b_id", name="distinct_players"),
        CheckConstraint("score_a >= 0 AND score_b >= 0", name="scores"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), nullable=False,
                                               index=True)
    round_name: Mapped[str] = mapped_column(String(60), nullable=False)
    participant_a_id: Mapped[int] = mapped_column(ForeignKey("tournament_participants.id"),
                                                  nullable=False)
    participant_b_id: Mapped[int] = mapped_column(ForeignKey("tournament_participants.id"),
                                                  nullable=False)
    score_a: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    score_b: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("tournament_participants.id"))
    created_at: Mapped[datetime] = created_at_col()
