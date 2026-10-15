from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from lecturepilot.app import create_app
from lecturepilot.canvas.canvas_workspace import CanvasWorkspace
from lecturepilot.core.db_models import (
    CourseRecord,
    SessionRecord,
)
from security_db_helpers import (
    LegacyUniversityAccounts,
    candidate,
    login,
    mutation_headers,
    seed_course_ref,
)


def test_course_owner_and_alma_ilias_enrollment_are_object_scoped(tmp_path: Path) -> None:
    alma = candidate("alma", "unit:100")
    ilias = candidate("ilias", "crs:200")
    app = _app(
        tmp_path,
        {
            "owner": [],
            "student-alma": [alma],
            "student-ilias": [ilias],
            "student-after-rename": [ilias],
            "nonmatching-student": [candidate("ilias", "crs:999", title="Secure Systems Lab")],
            "unrelated-professor": [candidate("alma", "unit:300", title="Other")],
        },
    )
    owner_client = TestClient(app, base_url="http://localhost:8000")
    owner = _professor_login(app, owner_client, "owner")
    created = owner_client.post(
        "/admin/course-workspaces",
        headers=mutation_headers(owner),
        json={
            "course_title": "Secure Systems",
            "target": "full-course",
            "access_policy": "tuebingen_enrolled",
        },
    )
    assert created.status_code == 200, created.json()
    course_id = created.json()["course"]["id"]
    assert len(course_id) == 36
    seed_course_ref(app.state.database, course_id, alma)
    seed_course_ref(app.state.database, course_id, ilias)

    unrelated_client = TestClient(app, base_url="http://localhost:8000")
    unrelated = _professor_login(app, unrelated_client, "unrelated-professor")
    denied = unrelated_client.get(f"/courses/{course_id}/source-bundle")
    assert denied.status_code == 403
    denied_routes = [
        unrelated_client.get(f"/admin/courses/{course_id}/lectures/lecture-01/analytics"),
        unrelated_client.post(
            f"/admin/courses/{course_id}/lectures/lecture-01/canvas/draft",
            headers={
                **mutation_headers(unrelated),
                "Idempotency-Key": "draft-request-key-denied-0001",
            },
        ),
        unrelated_client.delete(f"/admin/courses/{course_id}", headers=mutation_headers(unrelated)),
        unrelated_client.post(
            f"/admin/courses/{course_id}/materials",
            headers=mutation_headers(unrelated),
            data={"path": "notes.md"},
            files={"file": ("notes.md", b"private")},
        ),
    ]
    assert {response.status_code for response in denied_routes} == {403}

    enrolled_client = TestClient(app, base_url="http://localhost:8000")
    enrolled = login(enrolled_client, "student-ilias")
    alma_client = TestClient(app, base_url="http://localhost:8000")
    alma_enrolled = login(alma_client, "student-alma")
    with app.state.database.session() as database_session:
        course = database_session.get(CourseRecord, UUID(course_id))
        course.title = "Renamed Secure Systems"
    renamed_client = TestClient(app, base_url="http://localhost:8000")
    renamed_enrolled = login(renamed_client, "student-after-rename")
    wrong_client = TestClient(app, base_url="http://localhost:8000")
    wrong = login(wrong_client, "nonmatching-student")

    assert [course["id"] for course in enrolled["courses"]] == [course_id]
    assert [course["id"] for course in alma_enrolled["courses"]] == [course_id]
    assert [course["id"] for course in renamed_enrolled["courses"]] == [course_id]
    assert wrong["courses"] == []
    assert unrelated["roles"] == ["professor"]


def test_opaque_session_tokens_are_hashed_at_rest(tmp_path: Path) -> None:
    app = _app(tmp_path, {})
    client = TestClient(app, base_url="http://localhost:8000")
    session = login(client, "student-a")
    raw_token = client.cookies.get("lecturepilot_session")
    assert raw_token
    with app.state.database.session() as database_session:
        record = database_session.scalar(select(SessionRecord))
        assert record is not None
        assert record.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
        assert raw_token not in record.token_hash
        assert session["csrf_token"] not in record.csrf_hash
    termination = app.state.session_store.revoke(raw_token)
    assert termination is not None
    assert termination.reason == "manual_logout"
    assert termination.duration_ms >= 0


def _app(tmp_path: Path, courses_by_user: dict) -> object:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    app.state.legacy_accounts = LegacyUniversityAccounts(courses_by_user)
    return app


def _professor_login(app, client: TestClient, username: str) -> dict:
    app.state.legacy_accounts.roles_by_user[username] = "lecturer"
    return login(client, username)
