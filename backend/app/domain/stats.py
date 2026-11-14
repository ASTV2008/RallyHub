"""Cálculos puros para el dashboard. Las fórmulas están documentadas en docs/."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def clipped_minutes(start: datetime, end: datetime, win_start: datetime, win_end: datetime) -> float:
    """Minutos del intervalo [start,end) que caen dentro de [win_start,win_end)."""
    s, e = max(start, win_start), min(end, win_end)
    return max((e - s) / timedelta(minutes=1), 0.0)


def occupancy_by_table(
    reservations: Iterable[tuple[int, datetime, datetime]],
    table_ids: Iterable[int],
    win_start: datetime,
    win_end: datetime,
    capacity_minutes: int,
) -> dict[int, float]:
    """Ocupación (%) = minutos reservados en el período / minutos operativos disponibles.

    Complejidad O(R + T): un recorrido sobre reservas y uno sobre mesas, agrupando con dict.
    """
    booked: dict[int, float] = defaultdict(float)
    for table_id, s, e in reservations:
        booked[table_id] += clipped_minutes(s, e, win_start, win_end)
    result: dict[int, float] = {}
    for table_id in table_ids:
        pct = 0.0 if capacity_minutes <= 0 else booked[table_id] / capacity_minutes * 100
        result[table_id] = round(min(pct, 100.0), 1)
    return result


def attendance_rate(present: int, absent: int) -> float | None:
    """Asistencia (%) = PRESENT / (PRESENT + ABSENT). JUSTIFIED se excluye del denominador.

    Devuelve None cuando no hay registros (no se inventa un valor).
    """
    total = present + absent
    return None if total == 0 else round(present / total * 100, 1)


def count_by(items: Iterable[str]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for it in items:
        out[it] += 1
    return dict(out)


def local_day_bounds(now: datetime, tz: ZoneInfo) -> tuple[datetime, datetime]:
    local = now.astimezone(tz)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def local_week_bounds(now: datetime, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """Semana de lunes 00:00 a lunes siguiente 00:00 (hora local)."""
    day_start, _ = local_day_bounds(now, tz)
    monday = day_start - timedelta(days=day_start.weekday())
    return monday, monday + timedelta(days=7)
