#!/bin/sh
# Entrypoint del contenedor `app`. Un único proceso uvicorn => las migraciones y el seed se
# ejecutan una sola vez por arranque (no por worker). Ver README, sección "Migraciones".
set -e

python -m scripts.wait_for_db

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "Aplicando migraciones (alembic upgrade head)..."
  alembic upgrade head
fi

if [ "${SEED_DEMO:-0}" = "1" ]; then
  if [ "${ENVIRONMENT:-development}" = "production" ]; then
    echo "SEED_DEMO ignorado: ENVIRONMENT=production." >&2
  else
    echo "Cargando datos de demostración (idempotente)..."
    python -m scripts.seed
  fi
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers
