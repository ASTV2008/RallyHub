"""Autenticación por cookie HttpOnly + protección CSRF (double-submit con valor en el JWT)."""

import hmac
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.tokens import InvalidToken, decode_session_token
from app.db.session import get_db
from app.domain.errors import AuthenticationError, ForbiddenError
from app.models import User
from app.models.enums import Role

SESSION_COOKIE = "rh_session"
CSRF_COOKIE = "rh_csrf"
CSRF_HEADER = "x-csrf-token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def get_current_user(request: Request, db: Annotated[Session, Depends(get_db)],
                     settings: Annotated[Settings, Depends(get_settings)]) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise AuthenticationError("No autenticado.")
    try:
        claims = decode_session_token(settings.secret_key.get_secret_value(), token)
    except InvalidToken as exc:
        raise AuthenticationError("Sesión inválida o expirada.") from exc
    user = db.get(User, claims.user_id)
    if user is None or not user.is_active or user.token_version != claims.version:
        raise AuthenticationError("Sesión inválida o expirada.")
    if request.method not in SAFE_METHODS:
        sent = request.headers.get(CSRF_HEADER, "")
        if not sent or not hmac.compare_digest(sent, claims.csrf):
            raise ForbiddenError("Token CSRF inválido o ausente.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: Role):
    def dep(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError("No tiene permiso para realizar esta operación.")
        return user

    return dep


AdminUser = Annotated[User, Depends(require_role(Role.ADMIN))]
