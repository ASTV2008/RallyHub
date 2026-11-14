"""Logging estándar a stdout con formato uniforme. No se registran cuerpos ni contraseñas."""

from __future__ import annotations

import logging
import os
import sys


def configure_logging(level: str | None = None) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel((level or os.getenv("LOG_LEVEL") or "INFO").upper())
    access = logging.getLogger("uvicorn.access")
    access.handlers = []
    access.propagate = False  # el middleware ya registra cada petición con su request-id
