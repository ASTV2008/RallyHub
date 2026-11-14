from __future__ import annotations

from datetime import datetime

from pydantic import AwareDatetime, BaseModel, Field

from app.models.enums import TableStatus
from app.schemas.common import ORMModel


class FacilityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class FacilityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class FacilityRead(ORMModel):
    id: int
    name: str
    address: str | None
    description: str | None
    is_active: bool


class TableCreate(BaseModel):
    facility_id: int
    code: str = Field(min_length=1, max_length=30)
    table_type: str | None = Field(default=None, max_length=60)
    description: str | None = Field(default=None, max_length=2000)
    status: TableStatus = TableStatus.ACTIVE


class TableUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=30)
    table_type: str | None = Field(default=None, max_length=60)
    description: str | None = Field(default=None, max_length=2000)
    status: TableStatus | None = None


class TableRead(ORMModel):
    id: int
    facility_id: int
    facility_name: str
    code: str
    table_type: str | None
    description: str | None
    status: TableStatus


class MaintenanceCreate(BaseModel):
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    reason: str | None = Field(default=None, max_length=200)
    cancel_conflicts: bool = Field(
        default=False, description="Cancela las reservas confirmadas que se solapen con el bloqueo.")


class MaintenanceRead(ORMModel):
    id: int
    table_id: int
    starts_at: datetime
    ends_at: datetime
    reason: str | None


class BusySlot(BaseModel):
    kind: str  # RESERVATION | CLASS | MAINTENANCE
    starts_at: datetime
    ends_at: datetime


class TableAvailability(BaseModel):
    table_id: int
    code: str
    facility_id: int
    facility_name: str
    status: TableStatus
    available: bool
    reason: str | None = None
    busy: list[BusySlot] = []
