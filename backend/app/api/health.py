import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db.session import get_engine

router = APIRouter(prefix="/health", tags=["health"])
log = logging.getLogger("rallyhub.health")


@router.get("/live", summary="Liveness: el proceso responde")
def live():
    return {"status": "ok"}


@router.get("/ready", summary="Readiness: comprueba la conexión a MariaDB")
def ready():
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        log.exception("Readiness: la base de datos no responde")
        return JSONResponse(status_code=503,
                            content={"status": "unavailable", "checks": {"database": "error"}})
    return {"status": "ok", "checks": {"database": "ok"}}
