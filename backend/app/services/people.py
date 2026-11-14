from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.core.passwords import hash_password
from app.domain.errors import DuplicateError, ForbiddenError, NotFoundError
from app.models import Coach, Student, User
from app.models.enums import Role
from app.repositories.people import CoachRepository, StudentRepository, UserRepository
from app.schemas.people import CoachCreate, CoachRead, CoachUpdate, StudentCreate, StudentUpdate
from app.services.base import Service, require_roles

STUDENT_EDITABLE = {"first_name", "last_name", "phone", "guardian_name"}
COACH_EDITABLE = {"first_name", "last_name", "phone", "bio", "specialty"}


def _apply(obj, fields: dict, required: set[str]) -> None:
    for k, v in fields.items():
        if v is None and k in required:
            continue  # los campos obligatorios no se pueden vaciar
        setattr(obj, k, v)


class StudentService(Service):
    @property
    def repo(self) -> StudentRepository:
        return StudentRepository(self.db)

    def _can_view(self, actor: User, student: Student) -> bool:
        if actor.role == Role.ADMIN:
            return True
        if actor.role == Role.STUDENT:
            return student.user_id == actor.id
        if actor.role == Role.COACH and actor.coach:
            return self.repo.coach_teaches(actor.coach.id, student.id)
        return False

    def create(self, actor: User, data: StudentCreate) -> Student:
        require_roles(actor, Role.ADMIN)
        if UserRepository(self.db).by_email(data.email):
            raise DuplicateError("Ya existe un usuario con ese correo.")
        user = User(email=data.email, password_hash=hash_password(data.password),
                    role=Role.STUDENT, is_active=True, token_version=0)
        student = Student(user=user, first_name=data.first_name, last_name=data.last_name,
                          birth_date=data.birth_date, phone=data.phone,
                          guardian_name=data.guardian_name, level=data.level, is_active=True)
        try:
            self.db.add_all([user, student])
            self.db.flush()
            self.audit(actor, "CREATE", "student", student.id)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateError("Ya existe un usuario con ese correo.") from exc
        return self.repo.get_full(student.id)  # type: ignore[return-value]

    def get(self, actor: User, student_id: int) -> Student:
        student = self.repo.get_full(student_id)
        if student is None:
            raise NotFoundError("Estudiante no encontrado.")
        if not self._can_view(actor, student):
            raise ForbiddenError("No tiene permiso para ver este estudiante.")
        return student

    def search(self, actor: User, **filters):
        if actor.role == Role.ADMIN:
            return self.repo.search(coach_id=None, **filters)
        if actor.role == Role.COACH and actor.coach:
            return self.repo.search(coach_id=actor.coach.id, **filters)
        raise ForbiddenError("No tiene permiso para listar estudiantes.")

    def update(self, actor: User, student_id: int, data: StudentUpdate) -> Student:
        student = self.repo.get_full(student_id)
        if student is None:
            raise NotFoundError("Estudiante no encontrado.")
        fields = data.model_dump(exclude_unset=True)
        if actor.role == Role.ADMIN:
            pass
        elif actor.role == Role.STUDENT and student.user_id == actor.id:
            if set(fields) - STUDENT_EDITABLE:
                raise ForbiddenError("Solo puede modificar su nombre, teléfono y acudiente.")
        else:
            raise ForbiddenError("No tiene permiso para modificar este estudiante.")
        active = fields.pop("is_active", None)
        _apply(student, fields, {"first_name", "last_name", "level"})
        if active is not None and active != student.is_active:
            self._set_active(student, active)
        self.audit(actor, "UPDATE", "student", student.id, ",".join(sorted(fields)))
        self.db.commit()
        return self.repo.get_full(student_id)  # type: ignore[return-value]

    def deactivate(self, actor: User, student_id: int) -> None:
        """Baja lógica: se conserva el historial (reservas, asistencias, progreso)."""
        require_roles(actor, Role.ADMIN)
        student = self.repo.get_full(student_id)
        if student is None:
            raise NotFoundError("Estudiante no encontrado.")
        self._set_active(student, False)
        self.audit(actor, "DEACTIVATE", "student", student.id)
        self.db.commit()

    @staticmethod
    def _set_active(student: Student, active: bool) -> None:
        student.is_active = active
        student.user.is_active = active
        if not active:
            student.user.token_version += 1  # cierra sesiones abiertas


class CoachService(Service):
    @property
    def repo(self) -> CoachRepository:
        return CoachRepository(self.db)

    @staticmethod
    def present(actor: User, coach: Coach) -> CoachRead:
        """Contacto (correo/teléfono) solo para ADMIN o el propio entrenador."""
        out = CoachRead.model_validate(coach)
        if not (actor.role == Role.ADMIN or coach.user_id == actor.id):
            out.email = None
            out.phone = None
        return out

    def create(self, actor: User, data: CoachCreate) -> Coach:
        require_roles(actor, Role.ADMIN)
        if UserRepository(self.db).by_email(data.email):
            raise DuplicateError("Ya existe un usuario con ese correo.")
        user = User(email=data.email, password_hash=hash_password(data.password),
                    role=Role.COACH, is_active=True, token_version=0)
        coach = Coach(user=user, first_name=data.first_name, last_name=data.last_name,
                      specialty=data.specialty, bio=data.bio, phone=data.phone, is_active=True)
        try:
            self.db.add_all([user, coach])
            self.db.flush()
            self.audit(actor, "CREATE", "coach", coach.id)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateError("Ya existe un usuario con ese correo.") from exc
        return self.repo.get_full(coach.id)  # type: ignore[return-value]

    def get(self, actor: User, coach_id: int) -> Coach:
        coach = self.repo.get_full(coach_id)
        if coach is None:
            raise NotFoundError("Entrenador no encontrado.")
        return coach

    def update(self, actor: User, coach_id: int, data: CoachUpdate) -> Coach:
        coach = self.get(actor, coach_id)
        fields = data.model_dump(exclude_unset=True)
        if actor.role == Role.ADMIN:
            pass
        elif actor.role == Role.COACH and coach.user_id == actor.id:
            if set(fields) - COACH_EDITABLE:
                raise ForbiddenError("Solo puede modificar nombre, teléfono, biografía y especialidad.")
        else:
            raise ForbiddenError("No tiene permiso para modificar este entrenador.")
        active = fields.pop("is_active", None)
        _apply(coach, fields, {"first_name", "last_name"})
        if active is not None and active != coach.is_active:
            coach.is_active = active
            coach.user.is_active = active
            if not active:
                coach.user.token_version += 1
        self.audit(actor, "UPDATE", "coach", coach.id, ",".join(sorted(fields)))
        self.db.commit()
        return self.get(actor, coach_id)

    def deactivate(self, actor: User, coach_id: int) -> None:
        require_roles(actor, Role.ADMIN)
        coach = self.get(actor, coach_id)
        coach.is_active = False
        coach.user.is_active = False
        coach.user.token_version += 1
        self.audit(actor, "DEACTIVATE", "coach", coach.id)
        self.db.commit()
