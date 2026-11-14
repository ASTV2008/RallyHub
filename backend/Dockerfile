# syntax=docker/dockerfile:1
# Contexto de construcción: la RAÍZ del repositorio (ver compose.yaml).
# Etapas: base -> builder (ruedas) -> runtime (imagen final, no-root) -> dev (añade pytest/ruff).
FROM python:3.12.8-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app
WORKDIR /app

FROM base AS builder
COPY backend/requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

FROM base AS runtime
RUN groupadd --system --gid 10001 rally \
 && useradd --system --uid 10001 --gid rally --home-dir /app --shell /usr/sbin/nologin rally
COPY --from=builder /wheels /wheels
COPY backend/requirements.txt .
RUN pip install --no-index --find-links=/wheels -r requirements.txt && rm -rf /wheels
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini .
COPY scripts ./scripts
RUN chmod 0755 scripts/entrypoint.sh && chown -R rally:rally /app
USER rally
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)"
ENTRYPOINT ["/app/scripts/entrypoint.sh"]

FROM runtime AS dev
USER root
COPY backend/requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY backend/tests ./tests
COPY backend/pyproject.toml .
RUN chown -R rally:rally /app
USER rally
