"""Migraciones desde base vacía (ya aplicadas por la fixture de sesión) y seed idempotente."""
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import func, inspect, select

from app.db.base import Base
from app.db.session import get_engine, get_sessionmaker
from app.models import Attendance, ClassSession, Reservation, User

EXPECTED = {
    "users", "students", "coaches", "facilities", "tables", "maintenance_blocks", "reservations",
    "classes", "class_enrollments", "attendances", "progress_records", "tournaments",
    "tournament_participants", "tournament_matches", "audit_logs", "alembic_version",
}


def test_all_tables_exist_after_upgrade_head():
    assert set(inspect(get_engine()).get_table_names()) >= EXPECTED


def test_models_and_migration_agree_on_tables_and_columns():
    """Si alguien cambia un modelo sin crear migración, esta prueba falla."""
    with get_engine().connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    structural = [d for d in diff if isinstance(d, tuple) and d[0] in
                  {"add_table", "remove_table", "add_column", "remove_column"}]
    assert structural == [], structural


def test_innodb_and_utf8mb4():
    with get_engine().connect() as conn:
        rows = conn.exec_driver_sql(
            "SELECT ENGINE, TABLE_COLLATION FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'reservations'").all()
    engine, collation = rows[0]
    assert engine == "InnoDB" and collation.startswith("utf8mb4")


def test_seed_is_idempotent():
    from scripts import seed

    def counts():
        with get_sessionmaker()() as s:
            return tuple(s.scalar(select(func.count()).select_from(m)) for m in
                         (User, ClassSession, Reservation, Attendance))

    assert seed.main() == 0
    first = counts()
    assert first[0] >= 16 and first[1] >= 5 and first[2] >= 8
    assert seed.main() == 0
    assert counts() == first  # ejecutar de nuevo no duplica nada
