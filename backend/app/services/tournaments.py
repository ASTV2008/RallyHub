from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.domain.errors import (
    CapacityExceeded,
    ConflictError,
    DomainError,
    DuplicateError,
    ForbiddenError,
    NotFoundError,
    ResourceUnavailable,
)
from app.models import (
    Student,
    Tournament,
    TournamentMatch,
    TournamentParticipant,
    User,
)
from app.models.enums import Role, TournamentStatus
from app.repositories.people import StudentRepository
from app.schemas.tournaments import (
    MatchCreate,
    ParticipantCreate,
    TournamentCreate,
    TournamentRead,
    TournamentUpdate,
)
from app.services.base import Service, require_roles


class TournamentService(Service):
    def _counts(self, ids: list[int]) -> dict[int, int]:
        if not ids:
            return {}
        rows = self.db.execute(
            select(TournamentParticipant.tournament_id, func.count())
            .where(TournamentParticipant.tournament_id.in_(ids))
            .group_by(TournamentParticipant.tournament_id))
        return dict(rows.all())

    def _reads(self, items: list[Tournament]) -> list[TournamentRead]:
        counts = self._counts([t.id for t in items])
        return [TournamentRead.model_validate(t).model_copy(
            update={"participant_count": counts.get(t.id, 0)}) for t in items]

    def _get(self, tournament_id: int, lock: bool = False) -> Tournament:
        stmt = select(Tournament).where(Tournament.id == tournament_id)
        if lock:
            stmt = stmt.with_for_update()
        t = self.db.scalar(stmt)
        if t is None:
            raise NotFoundError("Torneo no encontrado.")
        return t

    def list_all(self, limit: int, offset: int) -> tuple[list[TournamentRead], int]:
        total = self.db.scalar(select(func.count()).select_from(Tournament)) or 0
        items = list(self.db.scalars(select(Tournament).order_by(Tournament.starts_on.desc(),
                                                                 Tournament.id)
                                     .limit(limit).offset(offset)))
        return self._reads(items), int(total)

    def get(self, tournament_id: int) -> TournamentRead:
        return self._reads([self._get(tournament_id)])[0]

    def create(self, actor: User, data: TournamentCreate) -> TournamentRead:
        require_roles(actor, Role.ADMIN)
        t = Tournament(**data.model_dump(), status=TournamentStatus.OPEN)
        self.db.add(t)
        self.db.flush()
        self.audit(actor, "CREATE", "tournament", t.id)
        self.db.commit()
        return self._reads([t])[0]

    def update(self, actor: User, tournament_id: int, data: TournamentUpdate) -> TournamentRead:
        require_roles(actor, Role.ADMIN)
        t = self._get(tournament_id, lock=True)
        fields = data.model_dump(exclude_unset=True)
        if fields.get("capacity") is not None:
            joined = self._counts([t.id]).get(t.id, 0)
            if fields["capacity"] < joined:
                raise CapacityExceeded("La capacidad no puede ser menor que los inscritos.")
        for k, v in fields.items():
            if v is None and k in {"name", "capacity", "status"}:
                continue
            setattr(t, k, v)
        self.audit(actor, "UPDATE", "tournament", t.id, ",".join(sorted(fields)))
        self.db.commit()
        return self._reads([t])[0]

    # --- participantes -----------------------------------------------------------------------
    def register(self, actor: User, tournament_id: int, data: ParticipantCreate
                 ) -> TournamentParticipant:
        students = StudentRepository(self.db)
        if actor.role == Role.STUDENT:
            me = students.by_user_id(actor.id)
            if me is None:
                raise ForbiddenError("Su usuario no tiene perfil de estudiante.")
            if data.student_id not in (None, me.id):
                raise ForbiddenError("Solo puede inscribirse usted mismo.")
            student = me
        elif actor.role == Role.ADMIN:
            if data.student_id is None:
                raise DomainError("Indique el estudiante (student_id).")
            found = students.get(data.student_id)
            if found is None:
                raise NotFoundError("Estudiante no encontrado.")
            student = found
        else:
            raise ForbiddenError("Su rol no puede inscribir participantes.")
        if not student.is_active:
            raise ResourceUnavailable("El estudiante está inactivo.")
        t = self._get(tournament_id, lock=True)  # protege el cupo
        if t.status != TournamentStatus.OPEN:
            raise ResourceUnavailable("El torneo no admite inscripciones.")
        if self._counts([t.id]).get(t.id, 0) >= t.capacity:
            raise CapacityExceeded("El torneo no tiene cupos disponibles.")
        try:
            part = TournamentParticipant(tournament_id=t.id, student_id=student.id)
            self.db.add(part)
            self.db.flush()
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateError("El estudiante ya está inscrito en el torneo.") from exc
        return self._participant(part.id)

    def _participant(self, participant_id: int) -> TournamentParticipant:
        p = self.db.scalar(select(TournamentParticipant).options(
            joinedload(TournamentParticipant.student)).where(
            TournamentParticipant.id == participant_id))
        if p is None:
            raise NotFoundError("Participante no encontrado.")
        return p

    def participants(self, tournament_id: int) -> list[TournamentParticipant]:
        self._get(tournament_id)
        return list(self.db.scalars(
            select(TournamentParticipant).options(joinedload(TournamentParticipant.student))
            .join(Student, Student.id == TournamentParticipant.student_id)
            .where(TournamentParticipant.tournament_id == tournament_id)
            .order_by(Student.last_name, Student.first_name)).unique())

    def withdraw(self, actor: User, tournament_id: int, participant_id: int) -> None:
        part = self._participant(participant_id)
        if part.tournament_id != tournament_id:
            raise NotFoundError("Participante no encontrado.")
        if actor.role == Role.STUDENT:
            if part.student.user_id != actor.id:
                raise ForbiddenError("Solo puede retirar su propia inscripción.")
        elif actor.role != Role.ADMIN:
            raise ForbiddenError("Su rol no puede retirar participantes.")
        t = self._get(tournament_id, lock=True)
        if t.status != TournamentStatus.OPEN:
            raise ConflictError("El torneo ya no admite retiros.")
        played = self.db.scalar(select(func.count()).select_from(TournamentMatch).where(
            (TournamentMatch.participant_a_id == participant_id)
            | (TournamentMatch.participant_b_id == participant_id)))
        if played:
            raise ConflictError("El participante ya tiene partidos registrados.")
        self.db.delete(part)
        self.db.commit()

    # --- resultados (registro manual; no hay generador de cuadros) -----------------------------
    def add_match(self, actor: User, tournament_id: int, data: MatchCreate) -> TournamentMatch:
        require_roles(actor, Role.ADMIN)
        t = self._get(tournament_id)
        if t.status in (TournamentStatus.CANCELLED, TournamentStatus.FINISHED):
            raise ConflictError("El torneo no admite nuevos resultados.")
        if data.participant_a_id == data.participant_b_id:
            raise DomainError("Los participantes deben ser distintos.")
        if data.score_a == data.score_b:
            raise DomainError("No se admiten empates en tenis de mesa.")
        ids = {data.participant_a_id, data.participant_b_id}
        found = set(self.db.scalars(select(TournamentParticipant.id).where(
            TournamentParticipant.id.in_(ids),
            TournamentParticipant.tournament_id == tournament_id)))
        if found != ids:
            raise NotFoundError("Los participantes deben pertenecer al torneo.")
        winner = data.participant_a_id if data.score_a > data.score_b else data.participant_b_id
        m = TournamentMatch(tournament_id=tournament_id, winner_id=winner, **data.model_dump())
        self.db.add(m)
        self.db.flush()
        self.audit(actor, "CREATE", "tournament_match", m.id)
        self.db.commit()
        return m

    def matches(self, tournament_id: int) -> list[TournamentMatch]:
        self._get(tournament_id)
        return list(self.db.scalars(select(TournamentMatch).where(
            TournamentMatch.tournament_id == tournament_id).order_by(TournamentMatch.id)))
