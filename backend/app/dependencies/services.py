"""Fábricas de servicios inyectables. El reloj es sustituible en pruebas (get_clock)."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.auth import AuthService
from app.services.base import Clock, system_clock
from app.services.classes import AttendanceService, ClassService, EnrollmentService
from app.services.dashboard import DashboardService
from app.services.facilities import FacilityService, TableService
from app.services.people import CoachService, StudentService
from app.services.progress import ProgressService
from app.services.reservations import ReservationService
from app.services.tournaments import TournamentService


def get_clock() -> Clock:
    return system_clock


def _factory(cls):
    def dep(db: Annotated[Session, Depends(get_db)], clock: Annotated[Clock, Depends(get_clock)]):
        return cls(db, clock=clock)

    return dep


AuthSvc = Annotated[AuthService, Depends(_factory(AuthService))]
StudentSvc = Annotated[StudentService, Depends(_factory(StudentService))]
CoachSvc = Annotated[CoachService, Depends(_factory(CoachService))]
FacilitySvc = Annotated[FacilityService, Depends(_factory(FacilityService))]
TableSvc = Annotated[TableService, Depends(_factory(TableService))]
ReservationSvc = Annotated[ReservationService, Depends(_factory(ReservationService))]
ClassSvc = Annotated[ClassService, Depends(_factory(ClassService))]
EnrollmentSvc = Annotated[EnrollmentService, Depends(_factory(EnrollmentService))]
AttendanceSvc = Annotated[AttendanceService, Depends(_factory(AttendanceService))]
ProgressSvc = Annotated[ProgressService, Depends(_factory(ProgressService))]
TournamentSvc = Annotated[TournamentService, Depends(_factory(TournamentService))]
DashboardSvc = Annotated[DashboardService, Depends(_factory(DashboardService))]


class Pager:
    def __init__(self, limit: Annotated[int, Query(ge=1, le=200)] = 50,
                 offset: Annotated[int, Query(ge=0)] = 0) -> None:
        self.limit = limit
        self.offset = offset


def page(items, total: int, pager: Pager) -> dict:
    """Respuesta paginada; FastAPI la valida contra Page[T] (from_attributes)."""
    return {"items": items, "total": total, "limit": pager.limit, "offset": pager.offset}
