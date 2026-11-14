import pytest

from app.core.ratelimit import LoginThrottle
from app.domain.errors import TooManyRequests


def test_blocks_after_max_failures_then_recovers_after_window():
    t = [0.0]
    th = LoginThrottle(max_attempts=3, window_seconds=60, clock=lambda: t[0])
    for _ in range(3):
        th.check("k")
        th.register_failure("k")
    with pytest.raises(TooManyRequests) as exc:
        th.check("k")
    assert exc.value.status_code == 429
    th.check("otra")  # claves independientes
    t[0] = 61.0
    th.check("k")  # la ventana venció


def test_success_resets_counter():
    th = LoginThrottle(max_attempts=1)
    th.register_failure("k")
    th.reset("k")
    th.check("k")


def test_memory_is_bounded():
    th = LoginThrottle(max_keys=5)
    for i in range(50):
        th.register_failure(f"k{i}")
    assert len(th._failures) <= 5
