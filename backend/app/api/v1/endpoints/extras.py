"""Progreso, torneos, dashboard y auditoría."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import AdminUser, CurrentUser
from app.dependencies.services import DashboardSvc, Pager, ProgressSvc, TournamentSvc, page
from app.models import AuditLog
from app.schemas.common import Page
from app.schemas.dashboard import (
    AdminDashboard,
    AuditRead,
    CoachDashboard,
    StudentDashboard,
)
from app.schemas.scheduling import ProgressCreate, ProgressRead, ProgressSummary
from app.schemas.tournaments import (
    MatchCreate,
    MatchRead,
    ParticipantCreate,
    ParticipantRead,
    TournamentCreate,
    TournamentRead,
    TournamentUpdate,
)

progress = APIRouter(prefix="/progress", tags=["progress"])
tournaments = APIRouter(prefix="/tournaments", tags=["tournaments"])
dashboard = APIRouter(prefix="/dashboard", tags=["dashboard"])
audit = APIRouter(prefix="/audit", tags=["audit"])


@progress.post("", response_model=ProgressRead, status_code=status.HTTP_201_CREATED,
               summary="Registrar observación de progreso (COACH de sus estudiantes)")
def create_progress(body: ProgressCreate, actor: CurrentUser, svc: ProgressSvc):
    return svc.create(actor, body)


@progress.get("/students/{student_id}", response_model=ProgressSummary,
              summary="Historial de progreso de un estudiante")
def student_progress(student_id: int, actor: CurrentUser, svc: ProgressSvc):
    return svc.summary(actor, student_id)


# --- torneos --------------------------------------------------------------------------------
@tournaments.get("", response_model=Page[TournamentRead], summary="Listar torneos")
def list_tournaments(_: CurrentUser, svc: TournamentSvc, pager: Annotated[Pager, Depends()]):
    items, total = svc.list_all(pager.limit, pager.offset)
    return page(items, total, pager)


@tournaments.post("", response_model=TournamentRead, status_code=status.HTTP_201_CREATED,
                  summary="Crear torneo (ADMIN)")
def create_tournament(body: TournamentCreate, actor: AdminUser, svc: TournamentSvc):
    return svc.create(actor, body)


@tournaments.get("/{tournament_id}", response_model=TournamentRead, summary="Consultar torneo")
def get_tournament(tournament_id: int, _: CurrentUser, svc: TournamentSvc):
    return svc.get(tournament_id)


@tournaments.patch("/{tournament_id}", response_model=TournamentRead,
                   summary="Actualizar torneo (ADMIN)")
def update_tournament(tournament_id: int, body: TournamentUpdate, actor: AdminUser,
                      svc: TournamentSvc):
    return svc.update(actor, tournament_id, body)


@tournaments.get("/{tournament_id}/participants", response_model=list[ParticipantRead],
                 summary="Participantes inscritos")
def participants(tournament_id: int, _: CurrentUser, svc: TournamentSvc):
    return svc.participants(tournament_id)


@tournaments.post("/{tournament_id}/participants", response_model=ParticipantRead,
                  status_code=status.HTTP_201_CREATED, summary="Inscribirse al torneo")
def register(tournament_id: int, body: ParticipantCreate, actor: CurrentUser, svc: TournamentSvc):
    return svc.register(actor, tournament_id, body)


@tournaments.delete("/{tournament_id}/participants/{participant_id}",
                    status_code=status.HTTP_204_NO_CONTENT, summary="Retirar inscripción")
def withdraw(tournament_id: int, participant_id: int, actor: CurrentUser, svc: TournamentSvc):
    svc.withdraw(actor, tournament_id, participant_id)


@tournaments.get("/{tournament_id}/matches", response_model=list[MatchRead],
                 summary="Resultados registrados")
def matches(tournament_id: int, _: CurrentUser, svc: TournamentSvc):
    return svc.matches(tournament_id)


@tournaments.post("/{tournament_id}/matches", response_model=MatchRead,
                  status_code=status.HTTP_201_CREATED,
                  summary="Registrar resultado de un partido (ADMIN; sin generador de cuadros)")
def add_match(tournament_id: int, body: MatchCreate, actor: AdminUser, svc: TournamentSvc):
    return svc.add_match(actor, tournament_id, body)


# --- dashboard ------------------------------------------------------------------------------
@dashboard.get("/admin", response_model=AdminDashboard, summary="Indicadores de administración")
def admin_dashboard(actor: AdminUser, svc: DashboardSvc):
    return svc.admin(actor)


@dashboard.get("/coach", response_model=CoachDashboard, summary="Indicadores del entrenador")
def coach_dashboard(actor: CurrentUser, svc: DashboardSvc):
    return svc.coach(actor)


@dashboard.get("/student", response_model=StudentDashboard, summary="Indicadores del estudiante")
def student_dashboard(actor: CurrentUser, svc: DashboardSvc):
    return svc.student(actor)


# --- auditoría ------------------------------------------------------------------------------
@audit.get("", response_model=Page[AuditRead], summary="Registro de auditoría (ADMIN)")
def list_audit(_: AdminUser, db: Annotated[Session, Depends(get_db)],
               pager: Annotated[Pager, Depends()]):
    total = db.scalar(select(func.count()).select_from(AuditLog)) or 0
    items = list(db.scalars(select(AuditLog).order_by(AuditLog.id.desc())
                            .limit(pager.limit).offset(pager.offset)))
    return page(items, int(total), pager)

