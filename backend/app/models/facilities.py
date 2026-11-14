from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UTCDateTime
from app.models._common import created_at_col, enum_col
from app.models.enums import TableStatus


class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    address: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = created_at_col()

    tables: Mapped[list[GameTable]] = relationship(back_populates="facility")


class GameTable(Base):
    """Mesa de tenis de mesa. Tabla SQL: `tables`.

    No existe estado RESERVED: la ocupación se deriva de reservas/clases/bloqueos.
    El código es único dentro de su instalación (ADR: unicidad por instalación).
    """

    __tablename__ = "tables"
    __table_args__ = (UniqueConstraint("facility_id", "code", name="uq_tables_facility_code"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), nullable=False,
                                             index=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    table_type: Mapped[str | None] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TableStatus] = mapped_column(
        enum_col(TableStatus, "table_status"), nullable=False, default=TableStatus.ACTIVE
    )
    created_at: Mapped[datetime] = created_at_col()

    facility: Mapped[Facility] = relationship(back_populates="tables")

    @property
    def facility_name(self) -> str:
        return self.facility.name


class MaintenanceBlock(Base):
    __tablename__ = "maintenance_blocks"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="range"),
        Index("ix_maintenance_blocks_table_range", "table_id", "starts_at", "ends_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(200))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = created_at_col()
