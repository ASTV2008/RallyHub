from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import AwareDatetime

from app.dependencies.auth import CurrentUser
from app.dependencies.services import (
    AttendanceSvc,
    ClassSvc,
    EnrollmentSvc,
    Pager,
    page,
)
from app.models.enums import ClassStatus, EnrollmentStatus, Level
from app.schemas.common import Page
from app.schemas.scheduling import (
    AttendanceCreate,
    AttendanceRead,
    AttendanceUpdate,
    ClassCreate,
    ClassRead,
    ClassUpdate,
    EnrollmentCreate,
    EnrollmentRead,
)

classes = APIRouter(prefix="/classes", tags=["classes"])
enrollments = APIRouter(prefix="/enrollments", tags=["enrollments"])
attendances = APIRouter(prefix="/attendances", tags=["attendances"])


@classes.get("", response_model=Page[ClassRead],
             summary="Listar clases (STUDENT: publicadas futuras; COACH: propias)")
def list_classes(actor: CurrentUser, svc: ClassSvc, pager: Annotated[Pager, Depends()],
                 status_filter: ClassStatus | None = None, level: Level | None = None,
                 date_from: AwareDatetime | None = None, date_to: AwareDatetime | None = None,
                 sort_by: str | None = None, order: Literal["asc", "desc"] = "asc"):
    items, total = svc.search(actor, status=status_filter, level=level, date_from=date_from,
                              date_to=date_to, sort_by=sort_by, order=order, limit=pager.limit,
                              offset=pager.offset)
    return page(items, total, pager)


@classes.post("", response_model=ClassRead, status_code=status.HTTP_201_CREATED,
              summary="Crear clase (ADMIN o COACH propio); nace en borrador")
def create_class(body: ClassCreate, actor: CurrentUser, svc: ClassSvc):
    return svc.create(actor, body)


@classes.get("/{class_id}", response_model=ClassRead, summary="Consultar clase")
def get_class(class_id: int, actor: CurrentUser, svc: ClassSvc):
    return svc.get(actor, class_id)


@classes.patch("/{class_id}", response_model=ClassRead, summary="Editar clase futura")
def update_class(class_id: int, body: ClassUpdate, actor: CurrentUser, svc: ClassSvc):
    return svc.update(actor, class_id, body)


@classes.post("/{class_id}/publish", response_model=ClassRead, summary="Publicar clase")
def publish_class(class_id: int, actor: CurrentUser, svc: ClassSvc):
    return svc.set_status(actor, class_id, ClassStatus.PUBLISHED)


@classes.post("/{class_id}/unpublish", response_model=ClassRead,
              summary="Ocultar clase (vuelve a borrador; sin inscritos)")
def unpublish_class(class_id: int, actor: CurrentUser, svc: ClassSvc):
    return svc.set_status(actor, class_id, ClassStatus.DRAFT)


@classes.post("/{class_id}/cancel", response_model=ClassRead, summary="Cancelar clase")
def cancel_class(class_id: int, actor: CurrentUser, svc: ClassSvc):
    return svc.set_status(actor, class_id, ClassStatus.CANCELLED)


# --- inscripciones --------------------------------------------------------------------------
@enrollments.get("", response_model=Page[EnrollmentRead], summary="Listar inscripciones")
def list_enrollments(actor: CurrentUser, svc: EnrollmentSvc, pager: Annotated[Pager, Depends()],
                     class_id: int | None = None, student_id: int | None = None,
                     status_filter: EnrollmentStatus | None = None):
    items, total = svc.search(actor, class_id=class_id, student_id=student_id,
                              status=status_filter, limit=pager.limit, offset=pager.offset)
    return page(items, total, pager)


@enrollments.post("", response_model=EnrollmentRead, status_code=status.HTTP_201_CREATED,
                  summary="Inscribir a una clase (409 si cupo lleno o duplicada)")
def enroll(body: EnrollmentCreate, actor: CurrentUser, svc: EnrollmentSvc):
    return svc.enroll(actor, body)


@enrollments.delete("/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT,
                    summary="Retirar inscripción")
def withdraw(enrollment_id: int, actor: CurrentUser, svc: EnrollmentSvc):
    svc.withdraw(actor, enrollment_id)


# --- asistencia -----------------------------------------------------------------------------
@attendances.get("", response_model=Page[AttendanceRead], summary="Consultar asistencia")
def list_attendance(actor: CurrentUser, svc: AttendanceSvc, pager: Annotated[Pager, Depends()],
                    class_id: int | None = None, student_id: int | None = None):
    items, total = svc.search(actor, class_id=class_id, student_id=student_id,
                              limit=pager.limit, offset=pager.offset)
    return page(items, total, pager)


@attendances.post("", response_model=AttendanceRead, status_code=status.HTTP_201_CREATED,
                  summary="Registrar asistencia (ADMIN o COACH de la clase)")
def record_attendance(body: AttendanceCreate, actor: CurrentUser, svc: AttendanceSvc):
    return svc.record(actor, body)


@attendances.patch("/{attendance_id}", response_model=AttendanceRead,
                   summary="Corregir asistencia (ADMIN o COACH de la clase)")
def correct_attendance(attendance_id: int, body: AttendanceUpdate, actor: CurrentUser,
                       svc: AttendanceSvc):
    return svc.update(actor, attendance_id, body)
