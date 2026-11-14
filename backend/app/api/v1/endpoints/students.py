from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth import AdminUser, CurrentUser
from app.dependencies.services import Pager, StudentSvc, page
from app.models.enums import Level
from app.schemas.common import Page
from app.schemas.people import StudentCreate, StudentRead, StudentUpdate

router = APIRouter(prefix="/students", tags=["students"])
Order = Literal["asc", "desc"]


@router.get("", response_model=Page[StudentRead], summary="Listar estudiantes (ADMIN; COACH: los suyos)")
def list_students(actor: CurrentUser, svc: StudentSvc, pager: Annotated[Pager, Depends()],
                  q: Annotated[str | None, Query(max_length=80)] = None,
                  level: Level | None = None, is_active: bool | None = None,
                  sort_by: str | None = None, order: Order = "asc"):
    items, total = svc.search(actor, q=q, level=level, is_active=is_active, sort_by=sort_by,
                              order=order, limit=pager.limit, offset=pager.offset)
    return page(items, total, pager)


@router.get("/export.csv", summary="Exportar estudiantes a CSV (ADMIN)")
def export_students(actor: AdminUser, svc: StudentSvc):
    from fastapi.responses import Response

    from app.domain.csv_utils import to_csv

    items, _ = svc.search(actor, q=None, level=None, is_active=None, sort_by=None, order="asc",
                          limit=5000, offset=0)
    rows = [(s.id, s.first_name, s.last_name, s.email, s.level.value,
             "SI" if s.is_active else "NO") for s in items]
    body = to_csv(["id", "nombre", "apellido", "correo", "nivel", "activo"], rows)
    return Response(body, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="estudiantes.csv"'})


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED,
             summary="Crear estudiante y su usuario (ADMIN)")
def create_student(body: StudentCreate, actor: AdminUser, svc: StudentSvc):
    return svc.create(actor, body)


@router.get("/{student_id}", response_model=StudentRead, summary="Consultar estudiante")
def get_student(student_id: int, actor: CurrentUser, svc: StudentSvc):
    return svc.get(actor, student_id)


@router.patch("/{student_id}", response_model=StudentRead, summary="Actualizar estudiante")
def update_student(student_id: int, body: StudentUpdate, actor: CurrentUser, svc: StudentSvc):
    return svc.update(actor, student_id, body)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Desactivar estudiante (baja lógica, ADMIN)")
def deactivate_student(student_id: int, actor: AdminUser, svc: StudentSvc):
    svc.deactivate(actor, student_id)
