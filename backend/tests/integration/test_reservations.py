"""Reservas: solapamientos, reglas de ventana, mantenimiento, cancelación y disponibilidad."""
from datetime import UTC, datetime, timedelta

import pytest

from app.models import Reservation
from app.models.enums import ReservationStatus, TableStatus
from tests.integration.helpers import iso, make_admin, make_student, make_table, slot

API = "/api/v1"


def book(client, table_id, start, end, **extra):
    return client.post(f"{API}/reservations", json={
        "table_id": table_id, "starts_at": iso(start), "ends_at": iso(end), **extra})


@pytest.fixture
def ctx(db, make_client):
    make_admin(db)
    s1, s2 = make_student(db, 1), make_student(db, 2)
    table = make_table(db)
    return {"table": table, "s1": s1, "s2": s2, "c1": make_client("student1@t.example"),
            "c2": make_client("student2@t.example"), "admin": make_client("admin@t.example")}


def test_valid_reservation_created(ctx):
    r = book(ctx["c1"], ctx["table"].id, slot(2, 10), slot(2, 11))
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "CONFIRMED" and body["student_id"] == ctx["s1"].id
    assert body["starts_at"].endswith("Z")  # salida siempre en UTC


@pytest.mark.parametrize(("start", "end", "ok"), [
    ((10, 30), (11, 30), False),   # solapamiento parcial (inicio dentro)
    ((9, 30), (10, 30), False),    # solapamiento parcial (fin dentro)
    ((10, 0), (11, 0), False),     # mismo horario
    ((9, 30), (11, 30), False),    # la nueva (120 min) contiene a la existente
    ((10, 15), (10, 45), False),   # la nueva está contenida
    ((11, 0), (12, 0), True),      # consecutiva posterior: permitida
    ((9, 0), (10, 0), True),       # consecutiva anterior: permitida
])
def test_overlap_matrix_against_existing_10_to_11(ctx, start, end, ok):
    assert book(ctx["c1"], ctx["table"].id, slot(2, 10), slot(2, 11)).status_code == 201
    r = book(ctx["c2"], ctx["table"].id, slot(2, *start), slot(2, *end))
    assert r.status_code == (201 if ok else 409), r.text
    if not ok:
        assert r.json()["code"] == "reservation_conflict"


def test_cancelled_reservation_frees_the_slot(ctx):
    first = book(ctx["c1"], ctx["table"].id, slot(3, 10), slot(3, 11)).json()
    assert ctx["c1"].post(f"{API}/reservations/{first['id']}/cancel").json()["status"] == "CANCELLED"
    assert book(ctx["c2"], ctx["table"].id, slot(3, 10), slot(3, 11)).status_code == 201


@pytest.mark.parametrize("status", [TableStatus.MAINTENANCE, TableStatus.OUT_OF_SERVICE])
def test_non_active_table_cannot_be_reserved(db, ctx, status):
    t = make_table(db, "T2", status)
    r = book(ctx["c1"], t.id, slot(2, 10), slot(2, 11))
    assert r.status_code == 409 and r.json()["code"] == "resource_unavailable"


def test_maintenance_block_prevents_reservation_and_needs_empty_agenda(ctx):
    admin, tid = ctx["admin"], ctx["table"].id
    r = admin.post(f"{API}/tables/{tid}/maintenance", json={
        "starts_at": iso(slot(4, 9)), "ends_at": iso(slot(4, 13)), "reason": "Cambio de red"})
    assert r.status_code == 201
    blocked = book(ctx["c1"], tid, slot(4, 10), slot(4, 11))
    assert blocked.status_code == 409 and blocked.json()["code"] == "resource_unavailable"
    assert book(ctx["c1"], tid, slot(4, 13), slot(4, 14)).status_code == 201  # fuera del bloqueo
    clash = admin.post(f"{API}/tables/{tid}/maintenance", json={
        "starts_at": iso(slot(4, 13)), "ends_at": iso(slot(4, 15))})
    assert clash.status_code == 409  # ya hay una reserva en ese rango


@pytest.mark.parametrize(("start", "end", "code"), [
    ((-1, (10, 0)), (-1, (11, 0)), "past_date"),
    ((2, (10, 0)), (2, (10, 0)), "invalid_interval"),
    ((2, (11, 0)), (2, (10, 0)), "invalid_interval"),
    ((2, (10, 0)), (2, (10, 15)), "duration_out_of_range"),
    ((2, (10, 0)), (2, (13, 0)), "duration_out_of_range"),
    ((2, (6, 0)), (2, (7, 0)), "outside_operating_hours"),
    ((2, (20, 30)), (2, (21, 30)), "outside_operating_hours"),
    ((60, (10, 0)), (60, (11, 0)), "advance_limit_exceeded"),
])
def test_booking_window_rules_return_400(ctx, start, end, code):
    r = book(ctx["c1"], ctx["table"].id, slot(start[0], *start[1]), slot(end[0], *end[1]))
    assert r.status_code == 400 and r.json()["code"] == code, r.text


def test_student_cannot_book_for_someone_else_nor_cancel_foreign(ctx):
    r = book(ctx["c1"], ctx["table"].id, slot(2, 10), slot(2, 11), student_id=ctx["s2"].id)
    assert r.status_code == 403
    mine = book(ctx["c1"], ctx["table"].id, slot(2, 10), slot(2, 11)).json()
    assert ctx["c2"].post(f"{API}/reservations/{mine['id']}/cancel").status_code == 403
    assert ctx["c2"].get(f"{API}/reservations/{mine['id']}").status_code == 403  # tampoco puede verla


def test_student_lists_only_own_reservations_admin_lists_all(ctx):
    book(ctx["c1"], ctx["table"].id, slot(2, 10), slot(2, 11))
    book(ctx["c2"], ctx["table"].id, slot(2, 12), slot(2, 13))
    assert ctx["c1"].get(f"{API}/reservations").json()["total"] == 1
    assert ctx["admin"].get(f"{API}/reservations").json()["total"] == 2


def test_admin_books_on_behalf_and_double_cancel_conflicts(ctx):
    r = book(ctx["admin"], ctx["table"].id, slot(2, 10), slot(2, 11), student_id=ctx["s1"].id)
    assert r.status_code == 201
    rid = r.json()["id"]
    assert ctx["admin"].post(f"{API}/reservations/{rid}/cancel").status_code == 200
    assert ctx["admin"].post(f"{API}/reservations/{rid}/cancel").status_code == 409


def test_student_cancellation_policy_blocks_late_cancel(db, ctx):
    # Reserva que empieza en ~1 h: se inserta directamente (la API valida el horario de operación).
    now = datetime.now(UTC)
    db.add(Reservation(student_id=ctx["s1"].id, table_id=ctx["table"].id,
                       starts_at=now + timedelta(hours=1), ends_at=now + timedelta(hours=2),
                       status=ReservationStatus.CONFIRMED))
    db.commit()
    rid = db.query(Reservation).one().id
    r = ctx["c1"].post(f"{API}/reservations/{rid}/cancel")
    assert r.status_code == 409 and r.json()["code"] == "cancellation_not_allowed"
    assert ctx["admin"].post(f"{API}/reservations/{rid}/cancel").status_code == 200  # el admin sí puede


def test_availability_is_computed_from_database(ctx):
    tid = ctx["table"].id
    book(ctx["c1"], tid, slot(2, 10), slot(2, 11))
    params = {"starts_at": iso(slot(2, 10, 30)), "ends_at": iso(slot(2, 11, 30))}
    busy = ctx["c2"].get(f"{API}/tables/{tid}/availability", params=params).json()
    assert busy["available"] is False and busy["busy"][0]["kind"] == "RESERVATION"
    free = ctx["c2"].get(f"{API}/tables/{tid}/availability", params={
        "starts_at": iso(slot(2, 11)), "ends_at": iso(slot(2, 12))}).json()
    assert free["available"] is True  # intervalo contiguo: sigue libre
    assert ctx["c2"].get(f"{API}/tables/availability", params=params).json()[0]["available"] is False


def test_naive_datetime_in_query_is_a_validation_error_not_500(ctx):
    r = ctx["c1"].get(f"{API}/reservations", params={"date_from": "2026-11-12T10:00:00"})
    assert r.status_code == 422


def test_record_is_persisted_in_utc(db, ctx):
    book(ctx["c1"], ctx["table"].id, slot(2, 10), slot(2, 11))
    stored = db.query(Reservation).one()
    assert stored.starts_at.utcoffset() == timedelta(0)
    assert stored.starts_at.hour == 15  # 10:00 Bogotá = 15:00 UTC
