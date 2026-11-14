from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth import AdminUser, CurrentUser
from app.dependencies.services import CoachSvc, Pager, page
from app.schemas.common import Page
from app.schemas.people import CoachCreate, CoachRead, CoachUpdate

router = APIRouter(prefix="/coaches", tags=["coaches"])


@router.get("", response_model=Page[CoachRead], summary="Listar entrenadores")
def list_coaches(actor: CurrentUser, svc: CoachSvc, pager: Annotated[Pager, Depends()],
                 q: Annotated[str | None, Query(max_length=80)] = None,
                 is_active: bool | None = None, sort_by: str | None = None,
                 order: Literal["asc", "desc"] = "asc"):
    items, total = svc.repo.search(q=q, is_active=is_active, sort_by=sort_by, order=order,
                                   limit=pager.limit, offset=pager.offset)
    return page([svc.present(actor, c) for c in items], total, pager)


@router.post("", response_model=CoachRead, status_code=status.HTTP_201_CREATED,
             summary="Crear entrenador y su usuario (ADMIN)")
def create_coach(body: CoachCreate, actor: AdminUser, svc: CoachSvc):
    return svc.present(actor, svc.create(actor, body))


@router.get("/{coach_id}", response_model=CoachRead, summary="Consultar entrenador")
def get_coach(coach_id: int, actor: CurrentUser, svc: CoachSvc):
    return svc.present(actor, svc.get(actor, coach_id))


@router.patch("/{coach_id}", response_model=CoachRead, summary="Actualizar entrenador")
def update_coach(coach_id: int, body: CoachUpdate, actor: CurrentUser, svc: CoachSvc):
    return svc.present(actor, svc.update(actor, coach_id, body))


@router.delete("/{coach_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Desactivar entrenador (baja lógica, ADMIN)")
def deactivate_coach(coach_id: int, actor: AdminUser, svc: CoachSvc):
    svc.deactivate(actor, coach_id)
