from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, Field

from app.models.enums import (
    AttendanceStatus,
    ClassStatus,
    EnrollmentStatus,
    Level,
    ReservationStatus,
)
from app.schemas.common import ORMModel


# --- reservas ---------------------------------------------------------------------------------
class ReservationCreate(BaseModel):
    table_id: int
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    notes: str | None = Field(default=None, max_length=300)
    student_id: int | None = None  # solo ADMIN; el estudiante reserva siempre para sí mismo


class ReservationStatusUpdate(BaseModel):
    status: ReservationStatus


class ReservationRead(ORMModel):
    id: int
    student_id: int
    student_name: str
    table_id: int
    table_code: str
    facility_name: str
    starts_at: datetime
    ends_at: datetime
    status: ReservationStatus
    notes: str | None
    created_at: datetime
    cancelled_at: datetime | None


# --- clases -----------------------------------------------------------------------------------
class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    coach_id: int | None = None  # ADMIN debe indicarlo; el entrenador usa su propio id
    table_id: int | None = None
    level: Level
    capacity: int = Field(ge=1, le=100)
    starts_at: AwareDatetime
    ends_at: AwareDatetime


class ClassUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    table_id: int | None = None
    clear_table: bool = False
    level: Level | None = None
    capacity: int | None = Field(default=None, ge=1, le=100)
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime | None = None


class ClassRead(ORMModel):
    id: int
    name: str
    description: str | None
    coach_id: int
    coach_name: str
    table_id: int | None
    table_code: str | None
    level: Level
    capacity: int
    starts_at: datetime
    ends_at: datetime
    status: ClassStatus
    enrolled_count: int = 0


class EnrollmentCreate(BaseModel):
    class_id: int
    student_id: int | None = None  # solo ADMIN


class EnrollmentRead(ORMModel):
    id: int
    class_id: int
    class_name: str
    class_starts_at: datetime
    student_id: int
    student_name: str
    status: EnrollmentStatus
    enrolled_at: datetime


class AttendanceCreate(BaseModel):
    enrollment_id: int
    status: AttendanceStatus
    notes: str | None = Field(default=None, max_length=300)


class AttendanceUpdate(BaseModel):
    status: AttendanceStatus | None = None
    notes: str | None = Field(default=None, max_length=300)


class AttendanceRead(ORMModel):
    id: int
    enrollment_id: int
    class_id: int
    student_id: int
    student_name: str
    status: AttendanceStatus
    notes: str | None
    recorded_at: datetime
    updated_at: datetime | None


# --- progreso ---------------------------------------------------------------------------------
Score = Annotated[int, Field(ge=1, le=5)]


class ProgressCreate(BaseModel):
    student_id: int
    recorded_on: date
    serve: Score
    receive: Score
    ball_control: Score
    movement: Score
    strategy: Score
    notes: str | None = Field(default=None, max_length=500)


class ProgressRead(ORMModel):
    id: int
    student_id: int
    coach_id: int
    recorded_on: date
    serve: int
    receive: int
    ball_control: int
    movement: int
    strategy: int
    notes: str | None


class ProgressSummary(BaseModel):
    student_id: int
    records: list[ProgressRead]
    sufficient_data: bool  # >= 2 observaciones para hablar de evolución
    first_average: float | None
    last_average: float | None
