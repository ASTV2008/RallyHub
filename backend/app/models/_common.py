from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum as PyEnum

from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import UTCDateTime


def enum_col(enum_cls: type[PyEnum], name: str) -> SAEnum:
    """Enum no nativo (VARCHAR + CHECK) almacenando el *valor* del enum."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=20,
        create_constraint=True,
        values_callable=lambda e: [m.value for m in e],
    )


def utcnow() -> datetime:
    return datetime.now(UTC)


def created_at_col() -> Mapped[datetime]:
    """Marca de creación asignada por la aplicación (sin DEFAULT de expresión en SQL)."""
    return mapped_column(UTCDateTime, nullable=False, default=utcnow)
