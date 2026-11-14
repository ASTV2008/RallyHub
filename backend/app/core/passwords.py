"""Hash de contraseñas con Argon2id (pwdlib)."""

from __future__ import annotations

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

_hasher = PasswordHash((Argon2Hasher(),))

# Hash precalculado para igualar tiempos cuando el email no existe (evita enumeración por timing).
_DUMMY_HASH = _hasher.hash("rallyhub-dummy-password-not-used")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _hasher.verify(password, _DUMMY_HASH)
        return False
    try:
        return _hasher.verify(password, password_hash)
    except Exception:  # hash corrupto: se trata como credencial inválida
        return False
