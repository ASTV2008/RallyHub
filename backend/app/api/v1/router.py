from fastapi import APIRouter

from app.api.v1.endpoints import auth, coaches, extras, facilities, reservations, students, tables
from app.api.v1.endpoints.classes import attendances, classes, enrollments

api_router = APIRouter()
for r in (auth.router, students.router, coaches.router, facilities.router, tables.router,
          reservations.router, classes, enrollments, attendances, extras.progress,
          extras.tournaments, extras.dashboard, extras.audit):
    api_router.include_router(r)
