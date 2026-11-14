from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import AwareDatetime

from app.dependencies.auth import AdminUser, CurrentUser
from app.dependencies.services import Pager, TableSvc, page
from app.models.enums import TableStatus
from app.schemas.common import Page
from app.schemas.facilities import (
    MaintenanceCreate,
    MaintenanceRead,
    TableAvailability,
    TableCreate,
    TableRead,
    TableUpdate,
)

router = APIRouter(prefix="/tables", tags=["tables"])


@router.get("", response_model=Page[TableRead], summary="Listar mesas")
def list_tables(_: CurrentUser, svc: TableSvc, pager: Annotated[Pager, Depends()],
                facility_id: int | None = None, status_: Annotated[TableStatus | None, Query(alias="status")] = None,
                q: Annotated[str | None, Query(max_length=30)] = None, sort_by: str | None = None,
                order: Literal["asc", "desc"] = "asc"):
    items, total = svc.repo.search(facility_id=facility_id, status=status_, q=q, sort_by=sort_by,
                                   order=order, limit=pager.limit, offset=pager.offset)
    return page(items, total, pager)


@router.get("/availability", response_model=list[TableAvailability],
            summary="Disponibilidad de mesas en un rango (calculada desde la base de datos)")
def availability(_: CurrentUser, svc: TableSvc, starts_at: AwareDatetime, ends_at: AwareDatetime,
                 facility_id: int | None = None):
    return svc.availability(starts_at, ends_at, facility_id=facility_id)


@router.post("", response_model=TableRead, status_code=status.HTTP_201_CREATED,
             summary="Crear mesa (ADMIN)")
def create_table(body: TableCreate, actor: AdminUser, svc: TableSvc):
    return svc.create(actor, body)


@router.get("/{table_id}", response_model=TableRead, summary="Consultar mesa")
def get_table(table_id: int, _: CurrentUser, svc: TableSvc):
    return svc.get(table_id)


@router.get("/{table_id}/availability", response_model=TableAvailability,
            summary="Disponibilidad de una mesa en un rango")
def table_availability(table_id: int, _: CurrentUser, svc: TableSvc, starts_at: AwareDatetime,
                       ends_at: AwareDatetime):
    return svc.availability(starts_at, ends_at, table_id=table_id)[0]


@router.patch("/{table_id}", response_model=TableRead, summary="Actualizar mesa (ADMIN)")
def update_table(table_id: int, body: TableUpdate, actor: AdminUser, svc: TableSvc,
                 cancel_reservations: bool = False):
    """409 `has_future_reservations` si pasar a MAINTENANCE/OUT_OF_SERVICE deja reservas futuras;
    con `cancel_reservations=true` se cancelan."""
    return svc.update(actor, table_id, body, cancel_reservations=cancel_reservations)


@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Dar de baja una mesa (queda OUT_OF_SERVICE, ADMIN)")
def retire_table(table_id: int, actor: AdminUser, svc: TableSvc, cancel_reservations: bool = False):
    svc.retire(actor, table_id, cancel_reservations=cancel_reservations)


@router.get("/{table_id}/maintenance", response_model=list[MaintenanceRead],
            summary="Bloqueos de mantenimiento de una mesa (ADMIN)")
def list_maintenance(table_id: int, _: AdminUser, svc: TableSvc):
    return svc.list_maintenance(table_id)


@router.post("/{table_id}/maintenance", response_model=MaintenanceRead,
             status_code=status.HTTP_201_CREATED, summary="Programar mantenimiento (ADMIN)")
def add_maintenance(table_id: int, body: MaintenanceCreate, actor: AdminUser, svc: TableSvc):
    return svc.add_maintenance(actor, table_id, body)


@router.delete("/{table_id}/maintenance/{block_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Eliminar bloqueo de mantenimiento (ADMIN)")
def remove_maintenance(table_id: int, block_id: int, actor: AdminUser, svc: TableSvc):
    svc.remove_maintenance(actor, table_id, block_id)
