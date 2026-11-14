from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import Modality, TournamentStatus
from app.schemas.common import ORMModel


class TournamentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str | None = Field(default=None, max_length=60)
    modality: Modality = Modality.SINGLES
    starts_on: date
    ends_on: date
    location: str | None = Field(default=None, max_length=200)
    capacity: int = Field(ge=2, le=512)

    @model_validator(mode="after")
    def _dates(self):
        if self.ends_on < self.starts_on:
            raise ValueError("La fecha de fin no puede ser anterior a la de inicio.")
        return self


class TournamentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: str | None = Field(default=None, max_length=60)
    location: str | None = Field(default=None, max_length=200)
    capacity: int | None = Field(default=None, ge=2, le=512)
    status: TournamentStatus | None = None


class TournamentRead(ORMModel):
    id: int
    name: str
    category: str | None
    modality: Modality
    starts_on: date
    ends_on: date
    location: str | None
    capacity: int
    status: TournamentStatus
    participant_count: int = 0


class ParticipantCreate(BaseModel):
    student_id: int | None = None  # solo ADMIN


class ParticipantRead(ORMModel):
    id: int
    tournament_id: int
    student_id: int
    student_name: str
    registered_at: datetime


class MatchCreate(BaseModel):
    round_name: str = Field(min_length=1, max_length=60)
    participant_a_id: int
    participant_b_id: int
    score_a: int = Field(ge=0, le=99)
    score_b: int = Field(ge=0, le=99)


class MatchRead(ORMModel):
    id: int
    tournament_id: int
    round_name: str
    participant_a_id: int
    participant_b_id: int
    score_a: int
    score_b: int
    winner_id: int | None
