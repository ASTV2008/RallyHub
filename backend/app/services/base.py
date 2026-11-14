from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.booking_rules import BookingPolicy
from app.domain.errors import ForbiddenError
from app.models import AuditLog, User
from app.models.enums import Role

Clock = Callable[[], datetime]


def system_clock() -> datetime:
    return datetime.now(UTC)


class Service:
    """Base de los casos de uso: sesión, configuración y reloj inyectables (testeables)."""

    def __init__(self, db: Session, settings: Settings | None = None,
                 clock: Clock | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.clock = clock or system_clock

    @property
    def policy(self) -> BookingPolicy:
        return self.settings.booking_policy

    def now(self) -> datetime:
        return self.clock()

    def audit(self, actor: User | None, action: str, entity: str, entity_id: int | None,
              detail: str | None = None) -> None:
        self.db.add(AuditLog(user_id=actor.id if actor else None, action=action, entity=entity,
                             entity_id=entity_id, detail=(detail or "")[:500] or None))


def require_roles(actor: User, *roles: Role) -> None:
    if actor.role not in roles:
        raise ForbiddenError("No tiene permiso para realizar esta operación.")
