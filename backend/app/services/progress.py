from __future__ import annotations

from sqlalchemy import select

from app.domain.errors import DomainError, ForbiddenError, NotFoundError
from app.models import ProgressRecord, User
from app.models.enums import Role
from app.models.progress import SKILLS
from app.repositories.people import StudentRepository
from app.schemas.scheduling import ProgressCreate, ProgressRead, ProgressSummary
from app.services.base import Service


def _average(rec: ProgressRecord) -> float:
    return round(sum(getattr(rec, s) for s in SKILLS) / len(SKILLS), 2)


class ProgressService(Service):
    def create(self, actor: User, data: ProgressCreate) -> ProgressRecord:
        if actor.role != Role.COACH or actor.coach is None:
            raise ForbiddenError("Solo un entrenador puede registrar progreso.")
        students = StudentRepository(self.db)
        if students.get(data.student_id) is None:
            raise NotFoundError("Estudiante no encontrado.")
        if not students.coach_teaches(actor.coach.id, data.student_id):
            raise ForbiddenError("Solo puede registrar progreso de estudiantes de sus clases.")
        today = self.now().astimezone(self.settings.tz).date()
        if data.recorded_on > today:
            raise DomainError("La fecha de la observación no puede ser futura.")
        rec = ProgressRecord(coach_id=actor.coach.id, **data.model_dump())
        self.db.add(rec)
        self.audit(None, "CREATE", "progress", None, f"student={data.student_id}")
        self.db.commit()
        return rec

    def summary(self, actor: User, student_id: int) -> ProgressSummary:
        students = StudentRepository(self.db)
        student = students.get(student_id)
        if student is None:
            raise NotFoundError("Estudiante no encontrado.")
        allowed = (
            actor.role == Role.ADMIN
            or (actor.role == Role.STUDENT and student.user_id == actor.id)
            or (actor.role == Role.COACH and actor.coach is not None
                and students.coach_teaches(actor.coach.id, student_id))
        )
        if not allowed:
            raise ForbiddenError("No tiene permiso para ver este progreso.")
        records = list(self.db.scalars(
            select(ProgressRecord).where(ProgressRecord.student_id == student_id)
            .order_by(ProgressRecord.recorded_on, ProgressRecord.id)))
        enough = len(records) >= 2  # no se muestra "evolución" con una sola observación
        return ProgressSummary(
            student_id=student_id,
            records=[ProgressRead.model_validate(r) for r in records],
            sufficient_data=enough,
            first_average=_average(records[0]) if records else None,
            last_average=_average(records[-1]) if records else None,
        )
