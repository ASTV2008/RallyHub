"""Configuración global de pytest.

Las pruebas unitarias (tests/unit) no requieren nada externo. Las de integración (tests/integration)
requieren MariaDB y un nombre de base que termine en `_test`; si faltan las dependencias
(FastAPI, SQLAlchemy...) se omiten en la recolección en lugar de fallar.
"""
import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-test-only-secret-key")

collect_ignore: list[str] = []
try:
    import fastapi  # noqa: F401
    import httpx  # noqa: F401
    import pwdlib  # noqa: F401
    import pymysql  # noqa: F401
    import sqlalchemy  # noqa: F401

    import alembic  # noqa: F401
except ImportError:
    collect_ignore.append("integration")  # directorio completo (incluye su conftest)
