from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import AwareDatetime

from app.core.config import Settings, get_settings
from app.dependencies.auth import AdminUser, CurrentUser
from app.dependencies.services import Pager, ReservationSvc, page
from app.models.enums import ReservationStatus
from app.schemas.common import Page
from app.schemas.scheduling import ReservationCreate, ReservationRead, ReservationStatusUpdate

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.get("", response_model=Page[ReservationRead],
            summary="Listar reservas (ADMIN: todas; STUDENT: propias; COACH: de sus estudiantes)")
def list_reservations(actor: CurrentUser, svc: ReservationSvc, pager: Annotated[Pager, Depends()],
                      table_id: int | None = None, facility_id: int | None = None,
                      student_id: int | None = None, status_filter: ReservationStatus | None = None,
                      date_from: AwareDatetime | None = None, date_to: AwareDatetime | None = None,
                      sort_by: str | None = None, order: Literal["asc", "desc"] = "asc"):
    items, total = svc.search(actor, table_id=table_id, facility_id=facility_id,
                              student_id=student_id, status=status_filter, date_from=date_from,
                              date_to=date_to, sort_by=sort_by, order=order, limit=pager.limit,
                              offset=pager.offset)
    return page(items, total, pager)


@router.get("/policy", summary="Política vigente de reservas y cancelación (visible en la interfaz)")
def reservation_policy(_: CurrentUser, settings: Annotated[Settings, Depends(get_settings)]):
    return {
        "timezone": settings.timezone,
        "opening_time": settings.opening_time.strftime("%H:%M"),
        "closing_time": settings.closing_time.strftime("%H:%M"),
        "min_minutes": settings.reservation_min_minutes,
        "max_minutes": settings.reservation_max_minutes,
        "max_advance_days": settings.reservation_max_advance_days,
        "cancel_min_hours_before": settings.cancel_min_hours_before,
    }


@router.get("/export.csv", summary="Exportar reservas a CSV (ADMIN)")
def export_reservations(actor: AdminUser, svc: ReservationSvc,
                        status_filter: ReservationStatus | None = None,
                        date_from: AwareDatetime | None = None, date_to: AwareDatetime | None = None):
    body = svc.export_csv(actor, status=status_filter, date_from=date_from, date_to=date_to)
    return Response(body, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="reservas.csv"'})


@router.post("", response_model=ReservationRead, status_code=status.HTTP_201_CREATED,
             summary="Crear reserva (409 si la mesa está ocupada)")
def create_reservation(body: ReservationCreate, actor: CurrentUser, svc: ReservationSvc):
    return svc.create(actor, body)


@router.get("/{reservation_id}", response_model=ReservationRead, summary="Consultar reserva")
def get_reservation(reservation_id: int, actor: CurrentUser, svc: ReservationSvc):
    return svc.get(actor, reservation_id)


@router.post("/{reservation_id}/cancel", response_model=ReservationRead,
             summary="Cancelar reserva (política: hasta 2 h antes para estudiantes)")
def cancel_reservation(reservation_id: int, actor: CurrentUser, svc: ReservationSvc):
    return svc.cancel(actor, reservation_id)


@router.patch("/{reservation_id}/status", response_model=ReservationRead,
              summary="Marcar COMPLETED o NO_SHOW (ADMIN)")
def set_outcome(reservation_id: int, body: ReservationStatusUpdate, actor: AdminUser,
                svc: ReservationSvc):
    return svc.set_outcome(actor, reservation_id, body.status)
