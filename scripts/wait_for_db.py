"""Espera a que MariaDB acepte conexiones (usado por el entrypoint del contenedor)."""

from __future__ import annotations

import os
import sys
import time

from sqlalchemy import create_engine, text

from app.core.config import get_settings


def main() -> int:
    timeout = int(os.getenv("DB_WAIT_SECONDS", "90"))
    engine = create_engine(get_settings().sqlalchemy_url)
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Base de datos disponible.", flush=True)
            return 0
        except Exception as exc:  # noqa: BLE001 - reintento deliberado
            last_error = type(exc).__name__
            time.sleep(2)
    print(f"No se pudo conectar a la base de datos en {timeout}s ({last_error}).",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
