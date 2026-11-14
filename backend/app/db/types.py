"""Tipos personalizados de columna."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.types import DateTime, TypeDecorator


class UTCDateTime(TypeDecorator):
    """Persiste instantes en UTC (DATETIME sin zona) y los devuelve *aware* en UTC.

    Rechaza datetimes naive para evitar ambigüedad de zona horaria.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Se requiere un datetime con zona horaria.")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect):
        return None if value is None else value.replace(tzinfo=UTC)
