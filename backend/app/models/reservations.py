from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UTCDateTime
from app.models._common import created_at_col, enum_col
from app.models.enums import ReservationStatus
from app.models.facilities import GameTable
from app.models.users import Student


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="range"),
        Index("ix_reservations_table_range", "table_id", "starts_at", "ends_at"),
        Index("ix_reservations_student_start", "student_id", "starts_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        enum_col(ReservationStatus, "reservation_status"),
        nullable=False,
        default=ReservationStatus.CONFIRMED,
    )
    notes: Mapped[str | None] = mapped_column(String(300))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = created_at_col()
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    student: Mapped[Student] = relationship()
    table: Mapped[GameTable] = relationship()

    @property
    def student_name(self) -> str:
        return self.student.full_name

    @property
    def table_code(self) -> str:
        return self.table.code

    @property
    def facility_name(self) -> str:
        return self.table.facility.name
