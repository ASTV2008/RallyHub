from __future__ import annotations

from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import Level
from app.schemas.common import ORMModel, check_password, check_phone


class _Person(BaseModel):
    @field_validator("phone", check_fields=False)
    @classmethod
    def _phone(cls, v):
        return check_phone(v)


class StudentCreate(_Person):
    email: EmailStr
    password: str
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    birth_date: date | None = None
    phone: str | None = None
    guardian_name: str | None = Field(default=None, max_length=120)
    level: Level = Level.BEGINNER

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return check_password(v)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.lower()


class StudentUpdate(_Person):
    """El estudiante solo puede modificar `phone` y `guardian_name` (se valida en el servicio)."""

    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    birth_date: date | None = None
    phone: str | None = None
    guardian_name: str | None = Field(default=None, max_length=120)
    level: Level | None = None
    is_active: bool | None = None


class StudentRead(ORMModel):
    id: int
    user_id: int
    email: str
    first_name: str
    last_name: str
    birth_date: date | None
    phone: str | None
    guardian_name: str | None
    level: Level
    is_active: bool


class CoachCreate(_Person):
    email: EmailStr
    password: str
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    specialty: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=2000)
    phone: str | None = None

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return check_password(v)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.lower()


class CoachUpdate(_Person):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    specialty: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=2000)
    phone: str | None = None
    is_active: bool | None = None


class CoachRead(ORMModel):
    id: int
    first_name: str
    last_name: str
    specialty: str | None
    bio: str | None
    is_active: bool
    email: str | None = None  # solo se informa a ADMIN o al propio entrenador
    phone: str | None = None  # idem
