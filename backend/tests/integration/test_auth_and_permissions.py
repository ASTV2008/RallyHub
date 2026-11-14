"""Autenticación, sesiones, CSRF y autorización por rol/propiedad (anti-IDOR)."""
from tests.integration.helpers import (
    PASSWORD,
    iso,
    make_admin,
    make_coach,
    make_student,
    make_table,
    slot,
)

API = "/api/v1"


def test_login_ok_sets_httponly_session_cookie_and_returns_profile(db, make_client):
    make_admin(db)
    c = make_client()
    r = c.post(f"{API}/auth/login", json={"email": "admin@t.example", "password": PASSWORD})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "ADMIN"
    set_cookie = " ".join(r.headers.get_list("set-cookie")).lower()
    assert "rh_session=" in set_cookie and "httponly" in set_cookie and "samesite=lax" in set_cookie
    assert "password" not in r.text.lower()  # nunca se devuelve la contraseña ni su hash


def test_login_wrong_password_and_unknown_user_same_message(db, make_client):
    make_admin(db)
    c = make_client()
    a = c.post(f"{API}/auth/login", json={"email": "admin@t.example", "password": "incorrecta-123"})
    b = c.post(f"{API}/auth/login", json={"email": "nadie@t.example", "password": "incorrecta-123"})
    assert a.status_code == b.status_code == 401
    assert a.json()["detail"] == b.json()["detail"]  # no permite enumerar usuarios


def test_inactive_user_cannot_login(db, make_client):
    admin = make_admin(db)
    admin.is_active = False
    db.commit()
    r = make_client().post(f"{API}/auth/login", json={"email": "admin@t.example", "password": PASSWORD})
    assert r.status_code == 401


def test_me_requires_authentication(make_client):
    assert make_client().get(f"{API}/auth/me").status_code == 401


def test_tampered_session_cookie_is_rejected(db, make_client):
    make_admin(db)
    c = make_client("admin@t.example")
    c.cookies.set("rh_session", "no.es.un.jwt")
    assert c.get(f"{API}/auth/me").status_code == 401


def test_write_without_csrf_header_is_forbidden(db, make_client):
    make_admin(db)
    c = make_client("admin@t.example")
    del c.headers["X-CSRF-Token"]
    r = c.post(f"{API}/facilities", json={"name": "Sede X"})
    assert r.status_code == 403 and "CSRF" in r.json()["detail"]


def test_foreign_origin_is_rejected(db, make_client):
    make_admin(db)
    c = make_client("admin@t.example")
    r = c.post(f"{API}/facilities", json={"name": "Sede X"}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_logout_invalidates_the_old_token(db, make_client):
    make_admin(db)
    c = make_client("admin@t.example")
    old = c.cookies.get("rh_session")
    assert c.post(f"{API}/auth/logout").status_code == 200
    stale = make_client()
    stale.cookies.set("rh_session", old)
    assert stale.get(f"{API}/auth/me").status_code == 401


def test_login_throttle_after_repeated_failures(db, make_client):
    make_admin(db)
    c = make_client()
    codes = [c.post(f"{API}/auth/login", json={"email": "admin@t.example", "password": "mala-clave-1"}).status_code
             for _ in range(7)]
    assert codes[:5] == [401] * 5 and codes[5:] == [429, 429]


def test_validation_error_does_not_echo_input(make_client, db):
    make_admin(db)
    c = make_client("admin@t.example")
    r = c.post(f"{API}/students", json={"email": "no-es-email", "password": "SecretoVisible123"})
    assert r.status_code == 422
    assert "SecretoVisible123" not in r.text


def test_student_cannot_read_another_student_idor(db, make_client):
    s1, s2 = make_student(db, 1), make_student(db, 2)
    c = make_client("student1@t.example")
    assert c.get(f"{API}/students/{s1.id}").status_code == 200
    assert c.get(f"{API}/students/{s2.id}").status_code == 403


def test_student_cannot_list_students_nor_manage_tables(db, make_client):
    make_student(db, 1)
    t = make_table(db)
    c = make_client("student1@t.example")
    assert c.get(f"{API}/students").status_code == 403
    assert c.post(f"{API}/tables", json={"facility_id": t.facility_id, "code": "X9"}).status_code == 403
    assert c.delete(f"{API}/tables/{t.id}").status_code == 403


def test_student_edits_only_allowed_profile_fields(db, make_client):
    s = make_student(db, 1)
    c = make_client("student1@t.example")
    assert c.patch(f"{API}/students/{s.id}", json={"phone": "300 123 4567"}).status_code == 200
    assert c.patch(f"{API}/students/{s.id}", json={"level": "ADVANCED"}).status_code == 403


def test_coach_cannot_modify_a_class_owned_by_another_coach(db, make_client):
    make_admin(db)
    make_coach(db, 1)
    make_coach(db, 2)
    admin = make_client("admin@t.example")
    coaches = admin.get(f"{API}/coaches").json()["items"]
    owner = next(x for x in coaches if x["first_name"] == "Coach1")
    r = admin.post(f"{API}/classes", json={
        "name": "Clase de Coach1", "coach_id": owner["id"], "level": "BEGINNER", "capacity": 4,
        "starts_at": iso(slot(2, 10)), "ends_at": iso(slot(2, 11))})
    assert r.status_code == 201, r.text
    other = make_client("coach2@t.example")
    assert other.patch(f"{API}/classes/{r.json()['id']}", json={"name": "Hack"}).status_code == 403
    mine = make_client("coach1@t.example")
    assert mine.patch(f"{API}/classes/{r.json()['id']}", json={"name": "Renombrada"}).status_code == 200


def test_admin_dashboard_forbidden_for_student(db, make_client):
    make_student(db, 1)
    assert make_client("student1@t.example").get(f"{API}/dashboard/admin").status_code == 403
