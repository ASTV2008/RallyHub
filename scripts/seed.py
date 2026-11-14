"""Datos de demostración (SOLO desarrollo). Idempotente y ficticio.

Uso: python -m scripts.seed
- Personas/instalaciones/mesas: se crean por clave natural (correo, nombre, código).
- Clases, reservas, asistencia, progreso y torneo: se crean una sola vez (marcador [DEMO]);
  ejecutar de nuevo no duplica nada.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.passwords import hash_password
from app.db.session import get_sessionmaker
from app.models import (
    Attendance,
    ClassEnrollment,
    ClassSession,
    Coach,
    Facility,
    GameTable,
    ProgressRecord,
    Reservation,
    Student,
    Tournament,
    TournamentMatch,
    TournamentParticipant,
    User,
)
from app.models.enums import (
    AttendanceStatus,
    ClassStatus,
    EnrollmentStatus,
    Level,
    ReservationStatus,
    Role,
    TableStatus,
    TournamentStatus,
)

DEMO = "[DEMO]"
# Credenciales de DEMOSTRACIÓN: no usar nunca en un despliegue real.
ADMIN_PASSWORD = "Admin-Demo-2026"
COACH_PASSWORD = "Coach-Demo-2026"
STUDENT_PASSWORD = "Student-Demo-2026"

COACHES = [
    ("coach1@rallyhub.demo", "Camila", "Rojas", "Técnica y servicio"),
    ("coach2@rallyhub.demo", "Mateo", "Herrera", "Preparación física y desplazamiento"),
    ("coach3@rallyhub.demo", "Laura", "Quintero", "Estrategia y competencia"),
]
STUDENTS = [
    ("estudiante1@rallyhub.demo", "Sofía", "Martínez", Level.BEGINNER),
    ("estudiante2@rallyhub.demo", "Daniel", "Gómez", Level.BEGINNER),
    ("estudiante3@rallyhub.demo", "Valentina", "Pardo", Level.BEGINNER),
    ("estudiante4@rallyhub.demo", "Andrés", "Cruz", Level.BEGINNER),
    ("estudiante5@rallyhub.demo", "Isabela", "Ortiz", Level.INTERMEDIATE),
    ("estudiante6@rallyhub.demo", "Samuel", "Vargas", Level.INTERMEDIATE),
    ("estudiante7@rallyhub.demo", "Mariana", "Silva", Level.INTERMEDIATE),
    ("estudiante8@rallyhub.demo", "Julián", "Peña", Level.INTERMEDIATE),
    ("estudiante9@rallyhub.demo", "Gabriela", "Mejía", Level.ADVANCED),
    ("estudiante10@rallyhub.demo", "Tomás", "Rincón", Level.ADVANCED),
    ("estudiante11@rallyhub.demo", "Luciana", "Duarte", Level.ADVANCED),
    ("estudiante12@rallyhub.demo", "Felipe", "Castaño", Level.BEGINNER),
]


def local_dt(tz, day_offset: int, hour: int, minute: int = 0) -> datetime:
    today = datetime.now(tz).date() + timedelta(days=day_offset)
    return datetime(today.year, today.month, today.day, hour, minute, tzinfo=tz).astimezone(UTC)


def get_or_create_user(db: Session, email: str, role: Role, password: str) -> tuple[User, bool]:
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user, False
    user = User(email=email, password_hash=hash_password(password), role=role,
                is_active=True, token_version=0)
    db.add(user)
    db.flush()
    return user, True


def seed_people(db: Session) -> tuple[list[Coach], list[Student]]:
    get_or_create_user(db, "admin@rallyhub.demo", Role.ADMIN, ADMIN_PASSWORD)
    coaches: list[Coach] = []
    for email, first, last, specialty in COACHES:
        user, _ = get_or_create_user(db, email, Role.COACH, COACH_PASSWORD)
        coach = db.scalar(select(Coach).where(Coach.user_id == user.id))
        if coach is None:
            coach = Coach(user_id=user.id, first_name=first, last_name=last, specialty=specialty,
                          bio="Entrenador ficticio de demostración.", is_active=True)
            db.add(coach)
            db.flush()
        coaches.append(coach)
    students: list[Student] = []
    for email, first, last, level in STUDENTS:
        user, _ = get_or_create_user(db, email, Role.STUDENT, STUDENT_PASSWORD)
        student = db.scalar(select(Student).where(Student.user_id == user.id))
        if student is None:
            student = Student(user_id=user.id, first_name=first, last_name=last, level=level,
                              is_active=True)
            db.add(student)
            db.flush()
        students.append(student)
    return coaches, students


def seed_facilities(db: Session) -> dict[str, GameTable]:
    layout = {
        "Sede Central": ("Calle 1 # 2-3 (dirección ficticia)",
                         [("C01", TableStatus.ACTIVE), ("C02", TableStatus.ACTIVE),
                          ("C03", TableStatus.ACTIVE), ("C04", TableStatus.ACTIVE),
                          ("C05", TableStatus.ACTIVE)]),
        "Sede Norte": ("Carrera 4 # 5-6 (dirección ficticia)",
                       [("N01", TableStatus.ACTIVE), ("N02", TableStatus.ACTIVE),
                        ("N03", TableStatus.MAINTENANCE)]),
    }
    tables: dict[str, GameTable] = {}
    for name, (address, items) in layout.items():
        fac = db.scalar(select(Facility).where(Facility.name == name))
        if fac is None:
            fac = Facility(name=name, address=address, description="Instalación de demostración.",
                           is_active=True)
            db.add(fac)
            db.flush()
        for code, status in items:
            t = db.scalar(select(GameTable).where(GameTable.facility_id == fac.id,
                                                  GameTable.code == code))
            if t is None:
                t = GameTable(facility_id=fac.id, code=code, table_type="Competición",
                              status=status)
                db.add(t)
                db.flush()
            tables[code] = t
    return tables


def seed_activity(db: Session, coaches: list[Coach], students: list[Student],
                  tables: dict[str, GameTable]) -> bool:
    already = db.scalar(select(func.count()).select_from(ClassSession).where(
        ClassSession.description.like(f"{DEMO}%")))
    if already:
        return False
    tz = get_settings().tz
    c1, c2, c3 = coaches
    spec = [  # nombre, coach, mesa, nivel, capacidad, día, hora inicio, hora fin, estado
        ("Fundamentos de servicio", c1, "C01", Level.BEGINNER, 6, 1, 16, 17, ClassStatus.PUBLISHED),
        ("Juego de devolución", c1, "C01", Level.INTERMEDIATE, 4, 2, 16, 17, ClassStatus.PUBLISHED),
        ("Desplazamiento y pies", c2, "C02", Level.INTERMEDIATE, 8, 3, 18, 19, ClassStatus.PUBLISHED),
        ("Estrategia de partido", c3, "N01", Level.ADVANCED, 3, 4, 17, 18, ClassStatus.PUBLISHED),
        ("Iniciación para nuevos (borrador)", c2, "C02", Level.BEGINNER, 10, 5, 9, 10, ClassStatus.DRAFT),
    ]
    sessions: list[ClassSession] = []
    for name, coach, code, level, cap, day, h0, h1, status in spec:
        s = ClassSession(name=name, description=f"{DEMO} Clase de demostración.", coach_id=coach.id,
                         table_id=tables[code].id, level=level, capacity=cap,
                         starts_at=local_dt(tz, day, h0), ends_at=local_dt(tz, day, h1),
                         status=status)
        db.add(s)
        sessions.append(s)
    past = ClassSession(name="Técnica base (sesión pasada)",
                        description=f"{DEMO} Sesión pasada con asistencia.", coach_id=c1.id,
                        table_id=tables["C03"].id, level=Level.BEGINNER, capacity=6,
                        starts_at=local_dt(tz, -3, 17), ends_at=local_dt(tz, -3, 18),
                        status=ClassStatus.PUBLISHED)
    db.add(past)
    db.flush()

    # Inscripciones (principiantes en clases de principiantes, etc.)
    for st in students[:4]:
        db.add(ClassEnrollment(class_id=sessions[0].id, student_id=st.id,
                               status=EnrollmentStatus.ENROLLED))
    for st in students[4:7]:
        db.add(ClassEnrollment(class_id=sessions[1].id, student_id=st.id,
                               status=EnrollmentStatus.ENROLLED))
    for st in students[8:11]:  # clase de capacidad 3: queda llena
        db.add(ClassEnrollment(class_id=sessions[3].id, student_id=st.id,
                               status=EnrollmentStatus.ENROLLED))
    past_enrollments = []
    for st in students[:4]:
        e = ClassEnrollment(class_id=past.id, student_id=st.id, status=EnrollmentStatus.ENROLLED)
        db.add(e)
        past_enrollments.append(e)
    db.flush()
    outcomes = [AttendanceStatus.PRESENT, AttendanceStatus.PRESENT, AttendanceStatus.ABSENT,
                AttendanceStatus.JUSTIFIED]
    for e, outcome in zip(past_enrollments, outcomes, strict=True):
        db.add(Attendance(enrollment_id=e.id, status=outcome, recorded_by=c1.user_id,
                          notes="Registro de demostración"))

    # Reservas (no se solapan con las clases anteriores)
    res_spec = [
        (students[4], "C04", 1, 10, 11, ReservationStatus.CONFIRMED),
        (students[5], "C04", 1, 11, 12, ReservationStatus.CONFIRMED),  # consecutiva
        (students[6], "C05", 2, 15, 16, ReservationStatus.CONFIRMED),
        (students[8], "N02", 3, 19, 20, ReservationStatus.CONFIRMED),
        (students[9], "C04", 4, 8, 9, ReservationStatus.CANCELLED),
        (students[10], "C05", -2, 14, 15, ReservationStatus.COMPLETED),
        (students[7], "C04", -1, 9, 10, ReservationStatus.COMPLETED),
        (students[11], "C05", 0, 20, 21, ReservationStatus.CONFIRMED),
    ]
    for st, code, day, h0, h1, res_status in res_spec:
        db.add(Reservation(student_id=st.id, table_id=tables[code].id,
                           starts_at=local_dt(tz, day, h0), ends_at=local_dt(tz, day, h1),
                           status=res_status, notes=f"{DEMO} reserva de demostración"))

    # Progreso: dos observaciones (hay evolución) y una sola (datos insuficientes)
    today = datetime.now(tz).date()
    for offs, scores in ((30, (2, 2, 3, 2, 1)), (3, (3, 3, 3, 3, 2))):
        db.add(ProgressRecord(student_id=students[0].id, coach_id=c1.id,
                              recorded_on=today - timedelta(days=offs), serve=scores[0],
                              receive=scores[1], ball_control=scores[2], movement=scores[3],
                              strategy=scores[4], notes="Observación de demostración"))
    db.add(ProgressRecord(student_id=students[1].id, coach_id=c1.id,
                          recorded_on=today - timedelta(days=3), serve=2, receive=2,
                          ball_control=2, movement=3, strategy=1,
                          notes="Observación de demostración"))
    return True


def seed_tournament(db: Session, students: list[Student]) -> None:
    name = "Copa RallyHub (demostración)"
    if db.scalar(select(Tournament).where(Tournament.name == name)):
        return
    today = datetime.now(get_settings().tz).date()
    t = Tournament(name=name, category="Abierta", starts_on=today + timedelta(days=14),
                   ends_on=today + timedelta(days=14), location="Sede Central",
                   capacity=8, status=TournamentStatus.OPEN)
    db.add(t)
    db.flush()
    parts = []
    for st in students[4:8]:
        p = TournamentParticipant(tournament_id=t.id, student_id=st.id)
        db.add(p)
        parts.append(p)
    db.flush()
    db.add(TournamentMatch(tournament_id=t.id, round_name="Semifinal",
                           participant_a_id=parts[0].id, participant_b_id=parts[1].id,
                           score_a=3, score_b=1, winner_id=parts[0].id))


def main() -> int:
    settings = get_settings()
    if settings.environment == "production":
        print("El seed de demostración está deshabilitado en producción.", file=sys.stderr)
        return 1
    with get_sessionmaker()() as db:
        coaches, students = seed_people(db)
        tables = seed_facilities(db)
        created = seed_activity(db, coaches, students, tables)
        seed_tournament(db, students)
        db.commit()
    print("Seed completado" + (" (datos de actividad creados)." if created
                               else " (ya existía; sin duplicados)."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
