from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.errors import DomainError

M = TypeVar("M")


class InvalidSortField(DomainError):
    code = "invalid_sort_field"


def apply_sort(stmt: Select, allowed: Mapping[str, Any], sort_by: str | None, order: str,
               default: str, tiebreak: Any) -> Select:
    """Ordena solo por campos de una lista blanca (evita ordenar por columnas arbitrarias)."""
    key = sort_by or default
    col = allowed.get(key)
    if col is None:
        raise InvalidSortField(f"Campo de ordenamiento no permitido: {key}. "
                               f"Permitidos: {', '.join(sorted(allowed))}.")
    primary = col.desc() if order == "desc" else col.asc()
    return stmt.order_by(primary, tiebreak.asc())


class BaseRepository(Generic[M]):
    model: type[M]

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, id_: int) -> M | None:
        return self.db.get(self.model, id_)

    def add(self, obj: M) -> M:
        self.db.add(obj)
        self.db.flush()
        return obj

    def paginate(self, stmt: Select, limit: int, offset: int) -> tuple[list[M], int]:
        total = self.db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
        items = self.db.scalars(stmt.limit(limit).offset(offset)).unique().all()
        return list(items), int(total or 0)


def like_pattern(q: str) -> str:
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
