from datetime import UTC, datetime, timedelta

import pytest

from app.core import tokens
from app.domain import csv_utils, stats

T0 = datetime(2026, 11, 9, 7, 0, tzinfo=UTC)


def test_occupancy_clips_to_window_and_groups_by_table():
    res = [
        (1, T0, T0 + timedelta(hours=2)),
        (1, T0 + timedelta(hours=3), T0 + timedelta(hours=4)),
        (2, T0 - timedelta(hours=1), T0 + timedelta(hours=1)),  # solo 1 h dentro de la ventana
    ]
    out = stats.occupancy_by_table(res, [1, 2, 3], T0, T0 + timedelta(hours=10), 600)
    assert out == {1: 30.0, 2: 10.0, 3: 0.0}


def test_occupancy_never_exceeds_100():
    out = stats.occupancy_by_table([(1, T0, T0 + timedelta(hours=20))], [1], T0, T0 + timedelta(hours=10), 60)
    assert out[1] == 100.0


def test_attendance_rate_excludes_justified_and_handles_empty():
    assert stats.attendance_rate(3, 1) == 75.0
    assert stats.attendance_rate(0, 0) is None


def test_count_by():
    assert stats.count_by(["A", "B", "A"]) == {"A": 2, "B": 1}


def test_week_bounds_monday_to_monday():
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("America/Bogota")
    start, end = stats.local_week_bounds(datetime(2026, 11, 11, 15, 0, tzinfo=tz), tz)  # miércoles
    assert start.weekday() == 0 and start.hour == 0 and end - start == timedelta(days=7)


@pytest.mark.parametrize("v", ["=1+1", "+cmd", "-1", "@SUM(A1)"])
def test_csv_formula_injection_neutralised(v):
    assert csv_utils.safe_cell(v).startswith("'")


def test_csv_output():
    out = csv_utils.to_csv(["a", "b"], [["x", "=evil()"], [None, 3]])
    assert out.splitlines() == ["a,b", "x,'=evil()", ",3"]


# --- tokens ---------------------------------------------------------------------------------
SECRET = "unit-test-secret-unit-test-secret-1234"


def test_token_roundtrip():
    tok = tokens.create_session_token(SECRET, 7, 2, "csrfvalue", 5)
    claims = tokens.decode_session_token(SECRET, tok)
    assert (claims.user_id, claims.version, claims.csrf) == (7, 2, "csrfvalue")


def test_token_wrong_secret_rejected():
    tok = tokens.create_session_token(SECRET, 7, 0, "c", 5)
    with pytest.raises(tokens.InvalidToken):
        tokens.decode_session_token("another-secret-another-secret-123456", tok)


def test_token_expired_rejected():
    old = datetime.now(UTC) - timedelta(hours=2)
    tok = tokens.create_session_token(SECRET, 7, 0, "c", 5, now=old)
    with pytest.raises(tokens.InvalidToken):
        tokens.decode_session_token(SECRET, tok)


def test_token_garbage_rejected():
    with pytest.raises(tokens.InvalidToken):
        tokens.decode_session_token(SECRET, "not-a-jwt")


def test_token_alg_none_rejected():
    import jwt

    forged = jwt.encode({"sub": "1", "ver": 0, "csrf": "c", "iss": "rallyhub",
                         "iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(minutes=5)},
                        key=None, algorithm="none")
    with pytest.raises(tokens.InvalidToken):
        tokens.decode_session_token(SECRET, forged)


def test_token_without_required_claims_rejected():
    import jwt

    bare = jwt.encode({"sub": "1", "exp": datetime.now(UTC) + timedelta(minutes=5)}, SECRET,
                      algorithm="HS256")
    with pytest.raises(tokens.InvalidToken):
        tokens.decode_session_token(SECRET, bare)
