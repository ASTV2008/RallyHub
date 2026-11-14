from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import Role
from app.schemas.common import ORMModel, check_password


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _norm(cls, v: str) -> str:
        return v.strip().lower()


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return check_password(v)


class ChangeEmailRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_email: EmailStr

    @field_validator("new_email")
    @classmethod
    def _norm(cls, v: str) -> str:
        return v.strip().lower()


class UserRead(ORMModel):
    id: int
    email: str
    role: Role
    is_active: bool


class MeRead(BaseModel):
    user: UserRead
    display_name: str
    student_id: int | None = None
    coach_id: int | None = None
