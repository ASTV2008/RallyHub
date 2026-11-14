"""Engine y sesión por solicitud.

Se usa READ COMMITTED: cada sentencia ve lo último confirmado. Con el nivel por defecto de
InnoDB (REPEATABLE READ) una lectura previa en la misma transacción (p. ej. al autenticar)
fijaría una instantánea anterior al bloqueo de la mesa y podría ocultar una reserva recién
confirmada por otra transacción. Ver docs/architecture/DECISIONES_ARQUITECTURA.md (ADR-6).
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    s = get_settings()
    return create_engine(
        s.sqlalchemy_url,
        isolation_level="READ COMMITTED",
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=s.db_pool_size,
        max_overflow=5,
    )


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dependencia FastAPI: una Session por solicitud; rollback ante cualquier excepción."""
    db = get_sessionmaker()()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
