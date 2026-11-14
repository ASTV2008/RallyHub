"""Mantenimiento/baja de mesas con agenda futura, desactivación de sedes y perfil propio."""
import pytest

from tests.integration.helpers import iso, make_admin, make_coach, make_student, make_table, slot

API = "/api/v1"


def book(client, table_id, start, end):
    return client.post(f"{API}/reservations", json={
        "table_id": table_id, "starts_at": iso(start), "ends_at": iso(end)})


def status_of(client, reservation_id):
    return client.get(f"{API}/reservations/{reservation_id}").json()["status"]


@pytest.fixture
def ctx(db, make_client):
    make_admin(db)
    make_student(db, 1)
    table = make_table(db)
    return {"table": table, "student": make_client("student1@t.example"),
            "admin": make_client("admin@t.example")}


def test_maintenance_over_confirmed_reservation_needs_explicit_cancel(ctx):
    admin, tid = ctx["admin"], ctx["table"].id
    rid = book(ctx["student"], tid, slot(4, 10), slot(4, 11)).json()["id"]
    body = {"starts_at": iso(slot(4, 9)), "ends_at": iso(slot(4, 12)), "reason": "Red nueva"}
    r = admin.post(f"{API}/tables/{tid}/maintenance", json=body)
    assert r.status_code == 409 and r.json()["code"] == "has_future_reservations"
    assert status_of(ctx["student"], rid) == "CONFIRMED"  # nada cambió
    r = admin.post(f"{API}/tables/{tid}/maintenance", json={**body, "cancel_conflicts": True})
    assert r.status_code == 201
    assert status_of(ctx["student"], rid) == "CANCELLED"
    blocked = book(ctx["student"], tid, slot(4, 10), slot(4, 11))
    assert blocked.status_code == 409 and blocked.json()["code"] == "resource_unavailable"


def test_maintenance_block_in_the_past_is_rejected(ctx):
    r = ctx["admin"].post(f"{API}/tables/{ctx['table'].id}/maintenance", json={
        "starts_at": iso(slot(-2, 9)), "ends_at": iso(slot(-2, 10))})
    assert r.status_code == 400 and r.json()["code"] == "past_date"


def test_maintenance_block_can_be_listed_and_removed(ctx):
    admin, tid = ctx["admin"], ctx["table"].id
    created = admin.post(f"{API}/tables/{tid}/maintenance", json={
        "starts_at": iso(slot(5, 9)), "ends_at": iso(slot(5, 11))}).json()
    assert [b["id"] for b in admin.get(f"{API}/tables/{tid}/maintenance").json()] == [created["id"]]
    assert admin.delete(f"{API}/tables/{tid}/maintenance/{created['id']}").status_code == 204
    assert admin.get(f"{API}/tables/{tid}/maintenance").json() == []
    assert book(ctx["student"], tid, slot(5, 9), slot(5, 10)).status_code == 201


def test_maintenance_endpoints_are_admin_only(ctx):
    tid = ctx["table"].id
    assert ctx["student"].get(f"{API}/tables/{tid}/maintenance").status_code == 403
    assert ctx["student"].post(f"{API}/tables/{tid}/maintenance", json={
        "starts_at": iso(slot(5, 9)), "ends_at": iso(slot(5, 11))}).status_code == 403


def test_changing_table_status_with_future_reservation_is_blocked_unless_confirmed(ctx):
    admin, tid = ctx["admin"], ctx["table"].id
    rid = book(ctx["student"], tid, slot(3, 10), slot(3, 11)).json()["id"]
    r = admin.patch(f"{API}/tables/{tid}", json={"status": "MAINTENANCE"})
    assert r.status_code == 409 and r.json()["code"] == "has_future_reservations"
    assert admin.get(f"{API}/tables/{tid}").json()["status"] == "ACTIVE"
    r = admin.patch(f"{API}/tables/{tid}", params={"cancel_reservations": "true"},
                    json={"status": "MAINTENANCE"})
    assert r.status_code == 200 and r.json()["status"] == "MAINTENANCE"
    assert status_of(ctx["student"], rid) == "CANCELLED"


def test_editing_table_data_does_not_touch_reservations(ctx):
    admin, tid = ctx["admin"], ctx["table"].id
    rid = book(ctx["student"], tid, slot(3, 10), slot(3, 11)).json()["id"]
    r = admin.patch(f"{API}/tables/{tid}", json={"table_type": "Competición"})
    assert r.status_code == 200 and r.json()["table_type"] == "Competición"
    assert status_of(ctx["student"], rid) == "CONFIRMED"


def test_retiring_table_with_future_reservation_needs_confirmation(ctx):
    admin, tid = ctx["admin"], ctx["table"].id
    rid = book(ctx["student"], tid, slot(3, 10), slot(3, 11)).json()["id"]
    r = admin.delete(f"{API}/tables/{tid}")
    assert r.status_code == 409 and r.json()["code"] == "has_future_reservations"
    assert admin.delete(f"{API}/tables/{tid}", params={"cancel_reservations": "true"}).status_code == 204
    assert admin.get(f"{API}/tables/{tid}").json()["status"] == "OUT_OF_SERVICE"
    assert status_of(ctx["student"], rid) == "CANCELLED"


def test_deactivating_facility_cancels_future_reservations_only_when_confirmed(ctx):
    admin, table = ctx["admin"], ctx["table"]
    rid = book(ctx["student"], table.id, slot(3, 10), slot(3, 11)).json()["id"]
    r = admin.delete(f"{API}/facilities/{table.facility_id}")
    assert r.status_code == 409 and r.json()["code"] == "has_future_reservations"
    assert admin.get(f"{API}/facilities/{table.facility_id}").json()["is_active"] is True
    ok = admin.delete(f"{API}/facilities/{table.facility_id}", params={"cancel_reservations": "true"})
    assert ok.status_code == 204
    assert admin.get(f"{API}/facilities/{table.facility_id}").json()["is_active"] is False
    assert status_of(ctx["student"], rid) == "CANCELLED"


def test_deactivating_empty_facility_needs_no_confirmation(ctx):
    table = ctx["table"]
    assert ctx["admin"].delete(f"{API}/facilities/{table.facility_id}").status_code == 204


# --- perfil propio ------------------------------------------------------------------------------
def test_student_and_coach_can_edit_their_own_name(db, make_client):
    make_admin(db)
    s = make_student(db, 1)
    c = make_coach(db, 1)
    sc = make_client("student1@t.example")
    r = sc.patch(f"{API}/students/{s.id}", json={"first_name": "Ana", "last_name": "Gómez"})
    assert r.status_code == 200 and r.json()["first_name"] == "Ana"
    assert sc.get(f"{API}/auth/me").json()["display_name"] == "Ana Gómez"
    cc = make_client("coach1@t.example")
    r = cc.patch(f"{API}/coaches/{c.id}", json={"first_name": "Luis", "specialty": "Defensa"})
    assert r.status_code == 200 and r.json()["first_name"] == "Luis"
    assert cc.patch(f"{API}/coaches/{c.id}", json={"is_active": False}).status_code == 403


def test_change_email_requires_password_and_unique_address(db, make_client):
    from tests.integration.helpers import PASSWORD

    make_admin(db)
    make_student(db, 1)
    make_student(db, 2)
    c = make_client("student1@t.example")
    url = f"{API}/auth/change-email"
    bad = c.post(url, json={"current_password": "otra-clave-mala1", "new_email": "n@t.example"})
    assert bad.status_code == 400 and bad.json()["code"] == "invalid_current_password"
    dup = c.post(url, json={"current_password": PASSWORD, "new_email": "student2@t.example"})
    assert dup.status_code == 409 and dup.json()["code"] == "duplicate"
    assert c.post(url, json={"current_password": PASSWORD, "new_email": "no-es-correo"}).status_code == 422
    ok = c.post(url, json={"current_password": PASSWORD, "new_email": "  Nuevo@T.Example "})
    assert ok.status_code == 200 and ok.json()["user"]["email"] == "nuevo@t.example"
    assert c.get(f"{API}/auth/me").json()["user"]["email"] == "nuevo@t.example"  # la sesión sigue vigente
    assert make_client("nuevo@t.example").get(f"{API}/auth/me").status_code == 200  # el nuevo correo inicia sesión


def test_change_password_invalidates_session_and_new_password_works(db, make_client):
    from tests.integration.helpers import PASSWORD

    make_admin(db)
    make_student(db, 1)
    c = make_client("student1@t.example")
    r = c.post(f"{API}/auth/change-password", json={"current_password": PASSWORD, "new_password": "Nueva-Clave-2026"})
    assert r.status_code == 200
    assert c.get(f"{API}/auth/me").status_code == 401
    assert make_client("student1@t.example", password="Nueva-Clave-2026").get(f"{API}/auth/me").status_code == 200
    old = make_client().post(f"{API}/auth/login", json={"email": "student1@t.example", "password": PASSWORD})
    assert old.status_code == 401


def test_wrong_current_password_keeps_the_session_alive(db, make_client):
    make_admin(db)
    make_student(db, 1)
    c = make_client("student1@t.example")
    r = c.post(f"{API}/auth/change-password", json={"current_password": "equivocada-123", "new_password": "Nueva-Clave-2026"})
    assert r.status_code == 400 and r.json()["code"] == "invalid_current_password"
    assert c.get(f"{API}/auth/me").status_code == 200
