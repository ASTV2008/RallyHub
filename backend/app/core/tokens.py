"""Token de sesión (JWT HS256, corta duración) y valor CSRF.

El valor CSRF viaja *dentro* del JWT firmado y también en una cookie legible por JS; el
servidor exige que la cabecera ``X-CSRF-Token`` coincida con el claim firmado (double-submit).
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

ALGORITHM = "HS256"
ISSUER = "rallyhub"


class InvalidToken(Exception):
    """Token ausente, malformado, firmado con otra clave o expirado."""


@dataclass(frozen=True)
class SessionClaims:
    user_id: int
    version: int
    csrf: str


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def create_session_token(
    secret: str, user_id: int, version: int, csrf: str, minutes: int, *, now: datetime | None = None
) -> str:
    issued = now or datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "ver": version,
        "csrf": csrf,
        "iss": ISSUER,
        "iat": issued,
        "exp": issued + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_session_token(secret: str, token: str) -> SessionClaims:
    try:
        data = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],  # lista explícita: rechaza alg=none y confusión de algoritmos
            issuer=ISSUER,
            options={"require": ["exp", "iat", "sub", "ver", "csrf"]},
        )
        return SessionClaims(user_id=int(data["sub"]), version=int(data["ver"]), csrf=str(data["csrf"]))
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise InvalidToken(str(exc)) from exc
