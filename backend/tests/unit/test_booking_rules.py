"""Reglas puras de reserva: solapamientos, ventana de reserva, horario y política de cancelación."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.domain import booking_rules as rules
from app.domain.errors import (
    AdvanceLimitExceeded,
    DurationOutOfRange,
    InvalidInterval,
    OutsideOperatingHours,
    PastDateError,
)

TZ = ZoneInfo("America/Bogota")
POLICY = rules.BookingPolicy(TZ, time(8, 0), time(21, 0), 30, 120, 30, 2)
NOW = datetime(2026, 11, 10, 9, 0, tzinfo=TZ)


def at(day: int, hh: int, mm: int = 0) -> datetime:
    return datetime(2026, 11, day, hh, mm, tzinfo=TZ)


A = (at(12, 10), at(12, 11))


@pytest.mark.parametrize(
    ("other", "expected"),
    [
        ((at(12, 10, 30), at(12, 11, 30)), True),  # solapamiento parcial (inicio dentro)
        ((at(12, 9, 30), at(12, 10, 30)), True),  # solapamiento parcial (fin dentro)
        ((at(12, 10), at(12, 11)), True),  # mismo horario
        ((at(12, 9), at(12, 12)), True),  # la nueva contiene a la existente
        ((at(12, 10, 15), at(12, 10, 45)), True),  # la nueva está contenida
        ((at(12, 11), at(12, 12)), False),  # consecutiva (después)
        ((at(12, 9), at(12, 10)), False),  # consecutiva (antes)
        ((at(12, 14), at(12, 15)), False),  # disjunta
    ],
)
def test_overlap_patterns(other, expected):
    assert rules.intervals_overlap(*A, *other) is expected
    assert rules.intervals_overlap(*other, *A) is expected  # simétrica


def test_valid_booking():
    rules.validate_booking_window(POLICY, at(12, 10), at(12, 11), NOW)


def test_booking_ending_exactly_at_closing_is_valid():
    rules.validate_booking_window(POLICY, at(12, 20), at(12, 21), NOW)


@pytest.mark.parametrize(
    ("start", "end", "exc"),
    [
        (at(12, 11), at(12, 10), InvalidInterval),
        (at(12, 10), at(12, 10), InvalidInterval),
        (at(10, 8), at(10, 9), PastDateError),
        (at(12, 10), at(12, 10, 15), DurationOutOfRange),
        (at(12, 10), at(12, 13), DurationOutOfRange),
        (at(12, 7), at(12, 8), OutsideOperatingHours),
        (at(12, 20), at(12, 21, 30), OutsideOperatingHours),
        (at(12, 23), at(13, 0, 30), OutsideOperatingHours),  # cruza medianoche
        (at(12, 10) + timedelta(days=40), at(12, 11) + timedelta(days=40), AdvanceLimitExceeded),
    ],
)
def test_invalid_booking(start, end, exc):
    with pytest.raises(exc):
        rules.validate_booking_window(POLICY, start, end, NOW)


def test_naive_datetimes_rejected():
    with pytest.raises(InvalidInterval):
        rules.validate_interval(datetime(2026, 11, 12, 10), datetime(2026, 11, 12, 11))


def test_operating_hours_are_evaluated_in_local_zone_not_utc():
    # 07:30 en Bogotá = 12:30 UTC: debe rechazarse aunque 12:30 "parezca" horario hábil en UTC.
    with pytest.raises(OutsideOperatingHours):
        rules.validate_booking_window(POLICY, at(12, 7, 30), at(12, 8, 30), NOW)


def test_class_window_has_no_duration_limit_but_needs_future_and_hours():
    rules.validate_class_window(POLICY, at(12, 17), at(12, 19, 30), NOW)
    with pytest.raises(PastDateError):
        rules.validate_class_window(POLICY, at(9, 10), at(9, 11), NOW)
    with pytest.raises(OutsideOperatingHours):
        rules.validate_class_window(POLICY, at(12, 20), at(12, 22), NOW)


def test_student_cancellation_window():
    assert rules.can_student_cancel(POLICY, NOW + timedelta(hours=3), NOW) is True
    assert rules.can_student_cancel(POLICY, NOW + timedelta(hours=2), NOW) is True  # límite inclusivo
    assert rules.can_student_cancel(POLICY, NOW + timedelta(hours=1), NOW) is False
