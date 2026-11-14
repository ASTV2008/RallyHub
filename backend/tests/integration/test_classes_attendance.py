"""Clases, inscripciones (cupo, duplicados, estados, conflictos) y asistencia."""
from datetime import UTC, datetime, timedelta

import pytest

from app.models import ClassSession
from app.models.enums import ClassStatus, Level
from tests.integration.helpers import iso, make_admin, make_coach, make_student, make_table, slot

API = "/api/v1"


@pytest.fixture
def ctx(db, make_client):
    make_admin(db)
    coach = make_coach(db, 1)
    return {"coach": coach, "table": make_table(db), "admin": make_client("admin@t.example"),
            "coach_c": make_client("coach1@t.example"), "make_client": make_client}


def new_class(ctx, day=2, h0=10, h1=11, capacity=2, publish=True, table=True, coach_id=None, client=None):
    body = {"name": "Clase", "level": "BEGINNER", "capacity": capacity,
            "starts_at": iso(slot(day, h0)), "ends_at": iso(slot(day, h1)),
            "coach_id": coach_id or ctx["coach"].id}
    if table:
        body["table_id"] = ctx["table"].id
    r = (client or ctx["admin"]).post(f"{API}/classes", json=body)
    assert r.status_code == 201, r.text
    if publish:
        p = (client or ctx["admin"]).post(f"{API}/classes/{r.json()['id']}/publish")
        assert p.status_code == 200, p.text
    return r.json()["id"]


def enroll(client, class_id, **extra):
    return client.post(f"{API}/enrollments", json={"class_id": class_id, **extra})


def test_enrollment_flow_capacity_and_duplicates(db, ctx):
    cid = new_class(ctx, capacity=2)
    students = [make_student(db, i) for i in (1, 2, 3)]
    clients = [ctx["make_client"](f"student{i}@t.example") for i in (1, 2, 3)]
    assert enroll(clients[0], cid).status_code == 201
    dup = enroll(clients[0], cid)
    assert dup.status_code == 409 and dup.json()["code"] == "duplicate"
    assert enroll(clients[1], cid).status_code == 201
    full = enroll(clients[2], cid)
    assert full.status_code == 409 and full.json()["code"] == "capacity_exceeded"
    assert ctx["admin"].get(f"{API}/classes/{cid}").json()["enrolled_count"] == 2
    # al retirarse se libera un cupo y se puede reinscribir
    enr = clients[0].get(f"{API}/enrollments").json()["items"][0]
    assert clients[0].delete(f"{API}/enrollments/{enr['id']}").status_code == 204
    assert enroll(clients[2], cid).status_code == 201
    assert students[0].id != students[1].id


def test_draft_and_cancelled_classes_reject_enrollment(db, ctx):
    make_student(db, 1)
    c = ctx["make_client"]("student1@t.example")
    draft = new_class(ctx, publish=False)
    assert enroll(c, draft).status_code == 409
    published = new_class(ctx, day=3)
    assert ctx["admin"].post(f"{API}/classes/{published}/cancel").status_code == 200
    assert enroll(c, published).status_code == 409


def test_student_only_sees_published_classes(db, ctx):
    make_student(db, 1)
    new_class(ctx, publish=False)
    new_class(ctx, day=3)
    assert ctx["make_client"]("student1@t.example").get(f"{API}/classes").json()["total"] == 1
    assert ctx["admin"].get(f"{API}/classes").json()["total"] == 2


def test_coach_schedule_conflict_and_table_conflict(db, ctx):
    new_class(ctx, day=2, h0=10, h1=11)
    other_table = make_table(db, "T9")
    same_coach = ctx["admin"].post(f"{API}/classes", json={
        "name": "Otra", "level": "BEGINNER", "capacity": 3, "coach_id": ctx["coach"].id,
        "table_id": other_table.id, "starts_at": iso(slot(2, 10, 30)), "ends_at": iso(slot(2, 11, 30))})
    assert same_coach.status_code == 409  # el entrenador ya tiene clase
    coach2 = make_coach(db, 2)
    same_table = ctx["admin"].post(f"{API}/classes", json={
        "name": "Otra", "level": "BEGINNER", "capacity": 3, "coach_id": coach2.id,
        "table_id": ctx["table"].id, "starts_at": iso(slot(2, 10, 30)), "ends_at": iso(slot(2, 11, 30))})
    assert same_table.status_code == 409 and same_table.json()["code"] == "reservation_conflict"


def test_class_blocks_table_reservations_and_vice_versa(db, ctx):
    make_student(db, 1)
    s = ctx["make_client"]("student1@t.example")
    new_class(ctx, day=2, h0=10, h1=11)
    r = s.post(f"{API}/reservations", json={"table_id": ctx["table"].id,
                                           "starts_at": iso(slot(2, 10)), "ends_at": iso(slot(2, 11))})
    assert r.status_code == 409
    assert s.post(f"{API}/reservations", json={"table_id": ctx["table"].id,
                                              "starts_at": iso(slot(2, 11)), "ends_at": iso(slot(2, 12))}).status_code == 201
    clash = ctx["admin"].post(f"{API}/classes", json={
        "name": "Choque", "level": "BEGINNER", "capacity": 3, "coach_id": ctx["coach"].id,
        "table_id": ctx["table"].id, "starts_at": iso(slot(2, 11, 30)), "ends_at": iso(slot(2, 12, 30))})
    assert clash.status_code == 409  # hay una reserva


def test_capacity_cannot_drop_below_enrolled(db, ctx):
    make_student(db, 1)
    cid = new_class(ctx, capacity=3)
    assert enroll(ctx["make_client"]("student1@t.example"), cid).status_code == 201
    assert ctx["admin"].patch(f"{API}/classes/{cid}", json={"capacity": 1}).status_code == 200
    assert ctx["admin"].patch(f"{API}/classes/{cid}", json={"capacity": 1}).status_code == 200
    assert ctx["admin"].patch(f"{API}/classes/{cid}", json={"capacity": 0}).status_code == 422


# --- asistencia -------------------------------------------------------------------------------
@pytest.fixture
def past(db, ctx):
    """Clase ya iniciada (se inserta directo: la API no permite programar en el pasado)."""
    now = datetime.now(UTC)
    cls = ClassSession(name="Pasada", coach_id=ctx["coach"].id, table_id=None, level=Level.BEGINNER,
                       capacity=5, starts_at=now - timedelta(hours=3), ends_at=now - timedelta(hours=2),
                       status=ClassStatus.PUBLISHED)
    db.add(cls)
    db.commit()
    st = make_student(db, 1)
    from app.models import ClassEnrollment

    enr = ClassEnrollment(class_id=cls.id, student_id=st.id)
    db.add(enr)
    db.commit()
    return enr


def test_attendance_record_duplicate_and_correction(past, ctx):
    r = ctx["coach_c"].post(f"{API}/attendances", json={"enrollment_id": past.id, "status": "PRESENT"})
    assert r.status_code == 201 and r.json()["student_id"] == past.student_id
    dup = ctx["coach_c"].post(f"{API}/attendances", json={"enrollment_id": past.id, "status": "ABSENT"})
    assert dup.status_code == 409
    fixed = ctx["coach_c"].patch(f"{API}/attendances/{r.json()['id']}", json={"status": "JUSTIFIED", "notes": "Cita médica"})
    assert fixed.status_code == 200 and fixed.json()["status"] == "JUSTIFIED"
    assert fixed.json()["updated_at"] is not None


def test_attendance_not_allowed_for_other_coach_or_student(db, past, ctx):
    make_coach(db, 2)
    other = ctx["make_client"]("coach2@t.example")
    assert other.post(f"{API}/attendances", json={"enrollment_id": past.id, "status": "PRESENT"}).status_code == 403
    student = ctx["make_client"]("student1@t.example")
    assert student.post(f"{API}/attendances", json={"enrollment_id": past.id, "status": "PRESENT"}).status_code == 403
    assert ctx["admin"].post(f"{API}/attendances", json={"enrollment_id": past.id, "status": "PRESENT"}).status_code == 201


def test_attendance_not_allowed_before_class_starts(db, ctx):
    make_student(db, 1)
    cid = new_class(ctx)
    enr = enroll(ctx["make_client"]("student1@t.example"), cid).json()
    r = ctx["coach_c"].post(f"{API}/attendances", json={"enrollment_id": enr["id"], "status": "PRESENT"})
    assert r.status_code == 409


def test_student_sees_only_own_attendance(db, past, ctx):
    ctx["coach_c"].post(f"{API}/attendances", json={"enrollment_id": past.id, "status": "PRESENT"})
    s = ctx["make_client"]("student1@t.example")
    assert s.get(f"{API}/attendances").json()["total"] == 1
    make_student(db, 2)
    assert ctx["make_client"]("student2@t.example").get(f"{API}/attendances").json()["total"] == 0
