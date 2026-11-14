"""Concurrencia: SELECT ... FOR UPDATE sobre la mesa serializa reservas simultáneas."""
import threading
from datetime import timedelta

from app.db.session import get_sessionmaker
from app.domain.errors import ReservationConflict
from app.models import Reservation, User
from app.schemas.scheduling import ReservationCreate
from app.services.reservations import ReservationService
from tests.integration.helpers import make_student, make_table, slot

THREADS = 10


def _race(table_id, requests):
    """Lanza una solicitud por hilo con una barrera para maximizar el solapamiento real."""
    barrier = threading.Barrier(len(requests))
    results: list[str] = [""] * len(requests)

    def worker(i, user_id, start, end):
        with get_sessionmaker()() as session:  # sesión (y transacción) propia por hilo
            user = session.get(User, user_id)
            svc = ReservationService(session)
            barrier.wait(timeout=10)
            try:
                svc.create(user, ReservationCreate(table_id=table_id, starts_at=start, ends_at=end))
                results[i] = "ok"
            except ReservationConflict:
                results[i] = "conflict"
            except Exception as exc:  # cualquier otra cosa es un defecto
                results[i] = f"error:{type(exc).__name__}:{exc}"

    threads = [threading.Thread(target=worker, args=(i, *r)) for i, r in enumerate(requests)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return results


def test_same_slot_only_one_of_many_concurrent_requests_succeeds(db):
    table = make_table(db)
    students = [make_student(db, i) for i in range(1, THREADS + 1)]
    start = slot(2, 10)
    res = _race(table.id, [(s.user_id, start, start + timedelta(hours=1)) for s in students])
    assert res.count("ok") == 1, res
    assert res.count("conflict") == THREADS - 1, res
    assert db.query(Reservation).count() == 1


def test_overlapping_but_different_intervals_never_double_book(db):
    table = make_table(db)
    students = [make_student(db, i) for i in range(1, 7)]
    base = slot(3, 10)
    # intervalos que se solapan en cadena: 10:00-11:00, 10:30-11:30, 11:00-12:00, ...
    reqs = [(s.user_id, base + timedelta(minutes=30 * i), base + timedelta(minutes=30 * i + 60))
            for i, s in enumerate(students)]
    res = _race(table.id, reqs)
    assert not [r for r in res if r.startswith("error")], res
    rows = sorted(db.query(Reservation).all(), key=lambda r: r.starts_at)
    for a, b in zip(rows, rows[1:], strict=False):
        assert a.ends_at <= b.starts_at, "dos reservas confirmadas se solapan"


def test_different_tables_do_not_block_each_other(db):
    t1, t2 = make_table(db, "A"), make_table(db, "B")
    s1, s2 = make_student(db, 1), make_student(db, 2)
    start = slot(2, 10)
    r1 = _race(t1.id, [(s1.user_id, start, start + timedelta(hours=1))])
    r2 = _race(t2.id, [(s2.user_id, start, start + timedelta(hours=1))])
    assert r1 == ["ok"] and r2 == ["ok"]
