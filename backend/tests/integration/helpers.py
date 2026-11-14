"""Fábricas de datos y utilidades de tiempo para las pruebas de integración."""
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.passwords import hash_password
from app.models import Coach, Facility, GameTable, Student, User
from app.models.enums import Level, Role, TableStatus

TZ = ZoneInfo("America/Bogota")
PASSWORD = "Test-Password-2026"
_HASH = hash_password(PASSWORD)  # se calcula una vez (Argon2 es deliberadamente lento)


def slot(day_offset: int, hour: int, minute: int = 0) -> datetime:
    """Instante aware en hora de Bogotá, `day_offset` días a partir de hoy (>= 1 => futuro)."""
    d = datetime.now(TZ).date() + timedelta(days=day_offset)
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=TZ)


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def make_user(db, email: str, role: Role) -> User:
    user = User(email=email, password_hash=_HASH, role=role, is_active=True, token_version=0)
    db.add(user)
    db.flush()
    return user


def make_admin(db, email="admin@t.example") -> User:
    u = make_user(db, email, Role.ADMIN)
    db.commit()
    return u


def make_student(db, n: int = 1, level: Level = Level.BEGINNER) -> Student:
    u = make_user(db, f"student{n}@t.example", Role.STUDENT)
    s = Student(user_id=u.id, first_name=f"Est{n}", last_name="Prueba", level=level, is_active=True)
    db.add(s)
    db.commit()
    return s


def make_coach(db, n: int = 1) -> Coach:
    u = make_user(db, f"coach{n}@t.example", Role.COACH)
    c = Coach(user_id=u.id, first_name=f"Coach{n}", last_name="Prueba", is_active=True)
    db.add(c)
    db.commit()
    return c


def make_table(db, code="T1", status=TableStatus.ACTIVE, facility: Facility | None = None) -> GameTable:
    if facility is None:
        facility = Facility(name=f"Sede-{code}", is_active=True)
        db.add(facility)
        db.flush()
    t = GameTable(facility_id=facility.id, code=code, status=status)
    db.add(t)
    db.commit()
    return t
