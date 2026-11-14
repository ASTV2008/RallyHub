from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.scheduling import ClassRead, ReservationRead


class TableOccupancy(BaseModel):
    table_id: int
    code: str
    facility_name: str
    occupancy_pct: float


class AdminDashboard(BaseModel):
    active_students: int
    active_coaches: int
    enabled_tables: int
    reservations_today: int
    reservations_week: int
    upcoming_classes: list[ClassRead]
    occupancy_period_days: int
    occupancy_by_table: list[TableOccupancy]
    attendance_period_days: int
    attendance_rate_pct: float | None
    students_by_level: dict[str, int]
    generated_at: datetime


class CoachDashboard(BaseModel):
    upcoming_classes: list[ClassRead]
    active_students: int
    attendance_period_days: int
    attendance_rate_pct: float | None
    generated_at: datetime


class StudentDashboard(BaseModel):
    upcoming_reservations: list[ReservationRead]
    upcoming_classes: list[ClassRead]
    attendance_period_days: int
    attendance_rate_pct: float | None
    generated_at: datetime


class AuditRead(BaseModel):
    id: int
    user_id: int | None
    action: str
    entity: str
    entity_id: int | None
    detail: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
