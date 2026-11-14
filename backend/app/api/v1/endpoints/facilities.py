from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth import AdminUser, CurrentUser
from app.dependencies.services import FacilitySvc, Pager, page
from app.schemas.common import Page
from app.schemas.facilities import FacilityCreate, FacilityRead, FacilityUpdate

router = APIRouter(prefix="/facilities", tags=["facilities"])


@router.get("", response_model=Page[FacilityRead], summary="Listar instalaciones")
def list_facilities(_: CurrentUser, svc: FacilitySvc, pager: Annotated[Pager, Depends()],
                    q: Annotated[str | None, Query(max_length=80)] = None,
                    is_active: bool | None = None, sort_by: str | None = None,
                    order: Literal["asc", "desc"] = "asc"):
    items, total = svc.repo.search(q=q, is_active=is_active, sort_by=sort_by, order=order,
                                   limit=pager.limit, offset=pager.offset)
    return page(items, total, pager)


@router.post("", response_model=FacilityRead, status_code=status.HTTP_201_CREATED,
             summary="Crear instalación (ADMIN)")
def create_facility(body: FacilityCreate, actor: AdminUser, svc: FacilitySvc):
    return svc.create(actor, body)


@router.get("/{facility_id}", response_model=FacilityRead, summary="Consultar instalación")
def get_facility(facility_id: int, _: CurrentUser, svc: FacilitySvc):
    return svc.get(facility_id)


@router.patch("/{facility_id}", response_model=FacilityRead, summary="Actualizar instalación (ADMIN)")
def update_facility(facility_id: int, body: FacilityUpdate, actor: AdminUser, svc: FacilitySvc,
                    cancel_reservations: bool = False):
    return svc.update(actor, facility_id, body, cancel_reservations=cancel_reservations)


@router.delete("/{facility_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Desactivar instalación (baja lógica, ADMIN)")
def deactivate_facility(facility_id: int, actor: AdminUser, svc: FacilitySvc,
                        cancel_reservations: bool = False):
    svc.deactivate(actor, facility_id, cancel_reservations=cancel_reservations)
