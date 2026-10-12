from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, select, update

from auth_helpers import professor_headers, student_headers
from lecturepilot.core.db_models import (
    AuditEventRecord,
    CourseSupportRequestRecord,
    ExternalIdentityRecord,
    TenantMembershipRecord,
    UserRecord,
)
from security_db_helpers import candidate, login, mutation_headers
from test_database_security import _app, _professor_login

requires_database = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="PostgreSQL test database is required"
)
ROUTE = "/me/course-support-requests"
ALMA = {"source": "alma", "external_course_id": "title:secure", "term": "Sommer 2026"}
ILIAS = {"source": "ilias", "external_course_id": "crs:200", "term": "Sommer 2026"}


def _courses() -> dict:
    secure = candidate("alma", "title:secure", title="INF-1234: Secure Systems")
    lab = candidate("ilias", "crs:200", title="Systems Lab")
    return {
        "student-a": [secure, lab],
        "student-b": [secure],
        "student-c": [secure],
        "student-none": [],
        "prof": [],
        "admin": [],
    }


def _client(app) -> TestClient:
    return TestClient(app, base_url="http://localhost:8000")


def _put(client: TestClient, session: dict, body: dict):
    return client.put(ROUTE, headers=mutation_headers(session), json=body)


def _delete(client: TestClient, session: dict, body: dict):
    return client.request("DELETE", ROUTE, headers=mutation_headers(session), json=body)


@requires_database
def test_students_request_only_their_observed_courses(tmp_path: Path) -> None:
    app = _app(tmp_path, _courses())
    client_a, client_b = _client(app), _client(app)
    student_a, student_b = login(client_a, "student-a"), login(client_b, "student-b")

    initial = client_a.get(ROUTE)
    assert initial.status_code == 200, initial.text
    assert {
        (item["source"], item["requested"], item["request_count"])
        for item in initial.json()["items"]
    } == {("alma", False, 0), ("ilias", False, 0)}

    forged = {**ALMA, "external_course_id": "title:not-mine"}
    assert _put(client_a, student_a, forged).status_code == 404
    assert _put(client_a, student_a, {**ALMA, "term": "Winter 2025"}).status_code == 404
    assert _put(client_b, student_b, ILIAS).status_code == 404
    assert client_a.put(ROUTE, json=ALMA).status_code == 403

    first = _put(client_a, student_a, ALMA)
    again = _put(client_a, student_a, ALMA)
    assert first.status_code == again.status_code == 200, first.text
    assert again.json() == {**ALMA, "requested": True, "request_count": 1}

    assert _put(client_b, student_b, ALMA).json()["request_count"] == 2
    listed = {item["source"]: item for item in client_a.get(ROUTE).json()["items"]}
    assert listed["alma"] == {**ALMA, "requested": True, "request_count": 2}
    assert listed["ilias"]["requested"] is False

    withdrawn = _delete(client_a, student_a, ALMA)
    assert withdrawn.status_code == 200
    assert withdrawn.json() == {**ALMA, "requested": False, "request_count": 1}
    assert _delete(client_a, student_a, ALMA).json()["request_count"] == 1
    assert _delete(client_a, student_a, forged).status_code == 404

    with app.state.database.session() as session:
        events = session.scalars(
            select(AuditEventRecord).where(AuditEventRecord.event_type.like("course_support.%"))
        ).all()
    assert sorted(event.event_type for event in events) == [
        "course_support.requested",
        "course_support.requested",
        "course_support.withdrawn",
    ]
    assert all(event.details == {"source": "alma"} for event in events)
    assert all("Secure" not in str(event.target_id) for event in events)


@requires_database
def test_course_requests_are_student_only(tmp_path: Path) -> None:
    app = _app(tmp_path, _courses())
    prof_client, student_client = _client(app), _client(app)
    professor = _professor_login(app, prof_client, "prof")
    student = login(student_client, "student-a")

    assert prof_client.get(ROUTE).status_code == 403
    assert _put(prof_client, professor, ALMA).status_code == 403
    preview = {**mutation_headers(student), "X-LecturePilot-Learner-Preview": "professor"}
    assert student_client.put(ROUTE, headers=preview, json=ALMA).status_code == 403


def test_course_requests_need_a_database_account(tmp_path: Path) -> None:
    app = _app(tmp_path, {})
    response = TestClient(app).get(ROUTE, headers=student_headers())
    assert response.status_code == 400


def test_demand_routes_check_roles_before_reading(tmp_path: Path) -> None:
    client = TestClient(_app(tmp_path, {}))
    demand = "/platform/course-support-demand"
    match = "/admin/course-support-demand/match?title=Secure"
    assert client.get(demand, headers=student_headers()).status_code == 403
    assert client.get(demand, headers=professor_headers()).status_code == 403
    assert client.get(match, headers=student_headers()).status_code == 403


@requires_database
def test_platform_demand_exposes_only_aggregates(tmp_path: Path) -> None:
    app = _app(tmp_path, _courses())
    prof_client = _client(app)
    created = prof_client.post(
        "/admin/course-workspaces",
        headers=mutation_headers(_professor_login(app, prof_client, "prof")),
        json={"course_title": "Secure Systems", "access_policy": "tuebingen_enrolled"},
    )
    assert created.status_code == 200, created.text
    clients = {name: _client(app) for name in ("student-a", "student-b", "student-c")}
    sessions = {name: login(client, name) for name, client in clients.items()}
    for name in ("student-a", "student-b"):
        assert _put(clients[name], sessions[name], ALMA).status_code == 200
    assert _put(clients["student-a"], sessions["student-a"], ILIAS).status_code == 200
    admin_client = _client(app)
    login(admin_client, "admin")
    _grant_platform_admin(app, "admin")
    login(admin_client, "admin")
    student_client = clients["student-a"]

    assert student_client.get("/platform/course-support-demand").status_code == 403
    response = admin_client.get("/platform/course-support-demand")
    assert response.status_code == 200, response.text
    rows = response.json()["items"]
    assert [(row["source"], row["request_count"], row["enrolled_user_count"]) for row in rows] == [
        ("alma", 2, 3),
        ("ilias", 1, 1),
    ]
    secure = rows[0]
    assert secure["title"] == "INF-1234: Secure Systems"
    assert secure["instructor"] == "Professor Example"
    assert secure["number"] == "SEC-1"
    assert [row["has_workspace"] for row in rows] == [True, False]
    assert secure["first_requested_at"] <= secure["last_requested_at"]
    assert set(secure) == {
        "source",
        "external_course_id",
        "term",
        "title",
        "number",
        "organization",
        "instructor",
        "display_url",
        "request_count",
        "enrolled_user_count",
        "has_workspace",
        "first_requested_at",
        "last_requested_at",
    }
    for name in sessions:
        assert name not in response.text
    with app.state.database.session() as session:
        user_ids = session.scalars(select(UserRecord.id)).all()
    assert all(str(user_id) not in response.text for user_id in user_ids)


@requires_database
def test_professor_builder_match_uses_course_title_key(tmp_path: Path) -> None:
    app = _app(tmp_path, _courses())
    for name in ("student-a", "student-c"):
        client = _client(app)
        assert _put(client, login(client, name), ALMA).status_code == 200
    late_client = _client(app)
    late_session = login(late_client, "student-b")
    prof_client = _client(app)
    _professor_login(app, prof_client, "prof")
    params = {"title": " secure   systems ", "term": "Sommer 2026"}

    matched = prof_client.get("/admin/course-support-demand/match", params=params)
    assert matched.status_code == 200, matched.text
    # Fewer than three requests could point at individuals, so professors see none yet.
    assert matched.json() == {"request_count": 0, "enrolled_user_count": 3}
    assert _put(late_client, late_session, ALMA).status_code == 200
    matched = prof_client.get("/admin/course-support-demand/match", params=params)
    assert matched.json() == {"request_count": 3, "enrolled_user_count": 3}
    other_term = prof_client.get(
        "/admin/course-support-demand/match",
        params={"title": "Secure Systems", "term": "Winter 2025"},
    )
    assert other_term.json() == {"request_count": 0, "enrolled_user_count": 0}


@requires_database
def test_account_deletion_removes_course_requests(tmp_path: Path) -> None:
    app = _app(tmp_path, _courses())
    client = _client(app)
    assert _put(client, login(client, "student-a"), ALMA).status_code == 200
    user_id = _user_id(app, "student-a")
    with app.state.database.session() as session:
        session.execute(delete(UserRecord).where(UserRecord.id == user_id))
    with app.state.database.session() as session:
        assert session.scalars(select(CourseSupportRequestRecord)).all() == []


def _user_id(app, username: str):
    with app.state.database.session() as session:
        return session.scalar(
            select(ExternalIdentityRecord.user_id).where(ExternalIdentityRecord.subject == username)
        )


def _grant_platform_admin(app, username: str) -> None:
    user_id = _user_id(app, username)
    with app.state.database.session() as session:
        session.execute(
            update(TenantMembershipRecord)
            .where(TenantMembershipRecord.user_id == user_id)
            .values(platform_admin=True)
        )
