from __future__ import annotations

import re
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class Message(BaseModel):
    detail: str


class ErrorBody(BaseModel):
    code: str
    detail: str


_PHONE = re.compile(r"^[0-9+()\-\s]{6,30}$")


def check_phone(v: str | None) -> str | None:
    if v is None or v == "":
        return None
    if not _PHONE.match(v):
        raise ValueError("Teléfono inválido (solo dígitos, espacios, +, -, paréntesis).")
    return v


def check_password(v: str) -> str:
    if len(v) < 10 or len(v) > 128:
        raise ValueError("La contraseña debe tener entre 10 y 128 caracteres.")
    if not (any(c.isalpha() for c in v) and any(c.isdigit() for c in v)):
        raise ValueError("La contraseña debe incluir letras y números.")
    return v
