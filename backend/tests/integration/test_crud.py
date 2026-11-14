"""CRUD administrativo: estudiantes, entrenadores, instalaciones y mesas."""
from tests.integration.helpers import make_admin

API = "/api/v1"
NEW = {"email": "Nueva.Persona@t.example", "password": "Clave-Segura-2026", "first_name": "Nueva",
       "last_name": "Persona", "level": "BEGINNER"}


def admin_client(db, make_client):
    make_admin(db)
    return make_client("admin@t.example")


def test_student_crud_lifecycle(db, make_client):
    c = admin_client(db, make_client)
    r = c.post(f"{API}/students", json=NEW)
    assert r.status_code == 201
    sid = r.json()["id"]
    assert r.json()["email"] == "nueva.persona@t.example"  # normalizado a minúsculas
    assert c.post(f"{API}/students", json=NEW).status_code == 409  # correo duplicado
    assert c.get(f"{API}/students/{sid}").status_code == 200
    assert c.patch(f"{API}/students/{sid}", json={"level": "INTERMEDIATE"}).json()["level"] == "INTERMEDIATE"
    assert c.delete(f"{API}/students/{sid}").status_code == 204
    assert c.get(f"{API}/students/{sid}").json()["is_active"] is False  # baja lógica: el registro persiste
    assert c.get(f"{API}/students/999999").status_code == 404


def test_student_validation_errors(db, make_client):
    c = admin_client(db, make_client)
    assert c.post(f"{API}/students", json={**NEW, "password": "corta"}).status_code == 422
    assert c.post(f"{API}/students", json={**NEW, "email": "malo"}).status_code == 422
    assert c.post(f"{API}/students", json={**NEW, "phone": "abc"}).status_code == 422


def test_student_listing_filters_pagination_and_sort_whitelist(db, make_client):
    c = admin_client(db, make_client)
    for i in range(3):
        assert c.post(f"{API}/students", json={**NEW, "email": f"p{i}@t.example", "first_name": f"N{i}"}).status_code == 201
    page = c.get(f"{API}/students", params={"limit": 2, "offset": 0, "sort_by": "first_name"}).json()
    assert page["total"] == 3 and len(page["items"]) == 2
    assert c.get(f"{API}/students", params={"sort_by": "password_hash"}).status_code == 400  # lista blanca
    assert c.get(f"{API}/students", params={"q": "N1"}).json()["total"] == 1
    assert c.get(f"{API}/students/export.csv").headers["content-type"].startswith("text/csv")


def test_coach_crud(db, make_client):
    c = admin_client(db, make_client)
    body = {"email": "c@t.example", "password": "Clave-Segura-2026", "first_name": "Ana", "last_name": "Coach"}
    r = c.post(f"{API}/coaches", json=body)
    assert r.status_code == 201
    assert c.post(f"{API}/coaches", json=body).status_code == 409
    assert c.delete(f"{API}/coaches/{r.json()['id']}").status_code == 204


def test_facility_and_table_crud_and_duplicate_code(db, make_client):
    c = admin_client(db, make_client)
    f = c.post(f"{API}/facilities", json={"name": "Sede Uno"})
    assert f.status_code == 201
    assert c.post(f"{API}/facilities", json={"name": "Sede Uno"}).status_code == 409
    fid = f.json()["id"]
    t = c.post(f"{API}/tables", json={"facility_id": fid, "code": "M1"})
    assert t.status_code == 201 and t.json()["facility_name"] == "Sede Uno"
    assert c.post(f"{API}/tables", json={"facility_id": fid, "code": "M1"}).status_code == 409
    assert c.patch(f"{API}/tables/{t.json()['id']}", json={"status": "MAINTENANCE"}).json()["status"] == "MAINTENANCE"
    assert c.delete(f"{API}/tables/{t.json()['id']}").status_code == 204
    assert c.get(f"{API}/tables/{t.json()['id']}").json()["status"] == "OUT_OF_SERVICE"
    assert c.post(f"{API}/tables", json={"facility_id": 9999, "code": "Z"}).status_code == 404
