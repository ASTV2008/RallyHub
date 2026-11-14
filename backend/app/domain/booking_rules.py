"""Reglas puras de reserva (sin base de datos ni HTTP).

Todas las comparaciones usan datetimes *aware*. La persistencia guarda UTC; las
reglas de horario de operación se evalúan en la zona horaria local del club.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.domain.errors import (
    AdvanceLimitExceeded,
    DurationOutOfRange,
    InvalidInterval,
    OutsideOperatingHours,
    PastDateError,
)


@dataclass(frozen=True)
class BookingPolicy:
    tz: ZoneInfo
    open_time: time
    close_time: time
    min_minutes: int
    max_minutes: int
    max_advance_days: int
    cancel_min_hours: int


def intervals_overlap(
    a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime
) -> bool:
    """Intervalos semiabiertos [inicio, fin). Dos reservas consecutivas NO se solapan."""
    return a_start < b_end and a_end > b_start


def _require_aware(*values: datetime) -> None:
    for v in values:
        if v.tzinfo is None or v.utcoffset() is None:
            raise InvalidInterval("Las fechas deben incluir zona horaria.")


def validate_interval(start: datetime, end: datetime) -> None:
    _require_aware(start, end)
    if end <= start:
        raise InvalidInterval("La hora de fin debe ser posterior a la hora de inicio.")


def validate_operating_hours(policy: BookingPolicy, start: datetime, end: datetime) -> None:
    ls, le = start.astimezone(policy.tz), end.astimezone(policy.tz)
    if ls.date() != le.date() or ls.time() < policy.open_time or le.time() > policy.close_time:
        raise OutsideOperatingHours(
            "El horario debe estar dentro del horario de operación "
            f"({policy.open_time:%H:%M}–{policy.close_time:%H:%M}) y en un solo día."
        )


def validate_not_past(start: datetime, now: datetime) -> None:
    if start < now:
        raise PastDateError("No se puede programar en el pasado.")


def validate_booking_window(
    policy: BookingPolicy, start: datetime, end: datetime, now: datetime
) -> None:
    """Valida una reserva de mesa completa (duración, pasado, antelación, horario)."""
    validate_interval(start, end)
    minutes = (end - start) / timedelta(minutes=1)
    if minutes < policy.min_minutes or minutes > policy.max_minutes:
        raise DurationOutOfRange(
            f"La duración debe estar entre {policy.min_minutes} y {policy.max_minutes} minutos."
        )
    validate_not_past(start, now)
    if start > now + timedelta(days=policy.max_advance_days):
        raise AdvanceLimitExceeded(
            f"Solo se puede reservar con hasta {policy.max_advance_days} días de antelación."
        )
    validate_operating_hours(policy, start, end)


def validate_class_window(
    policy: BookingPolicy, start: datetime, end: datetime, now: datetime
) -> None:
    """Una clase respeta fin>inicio, futuro y horario de operación (sin límites de duración)."""
    validate_interval(start, end)
    validate_not_past(start, now)
    validate_operating_hours(policy, start, end)


def can_student_cancel(policy: BookingPolicy, start: datetime, now: datetime) -> bool:
    """Política: el estudiante cancela hasta `cancel_min_hours` antes del inicio."""
    return now <= start - timedelta(hours=policy.cancel_min_hours)
