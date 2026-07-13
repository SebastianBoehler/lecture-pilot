from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.db_models import (
    CourseEnrollmentRecord,
    ExternalIdentityRecord,
    CourseRecord,
    SessionRecord,
)
from lecturepilot.external_course_sync import sync_external_courses
from lecturepilot.identity_repository import IdentityRepository
from lecturepilot.university_models import ExternalCourseSource, UniversityLoginResult
from security_db_helpers import FakeUniversityAdapter, candidate, login, mutation_headers


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

    unrelated_client = TestClient(app, base_url="http://localhost:8000")
    unrelated = _professor_login(app, unrelated_client, "unrelated-professor")
    denied = unrelated_client.get(f"/courses/{course_id}/source-bundle")
    assert denied.status_code == 403
    denied_routes = [
        unrelated_client.get(f"/admin/courses/{course_id}/lectures/lecture-01/analytics"),
        unrelated_client.post(
            f"/admin/courses/{course_id}/lectures/lecture-01/canvas/draft",
            headers=mutation_headers(unrelated),
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


def test_ambiguous_title_and_term_match_fails_closed(tmp_path: Path) -> None:
    upstream = candidate("ilias", "crs:404", title="Duplicate Course")
    app = _app(tmp_path, {"student": [upstream]})
    for username in ("owner-a", "owner-b"):
        owner_client = TestClient(app, base_url="http://localhost:8000")
        owner = _professor_login(app, owner_client, username)
        response = owner_client.post(
            "/admin/course-workspaces",
            headers=mutation_headers(owner),
            json={
                "course_title": "Duplicate Course",
                "target": "full-course",
                "access_policy": "tuebingen_enrolled",
            },
        )
        assert response.status_code == 200

    student_client = TestClient(app, base_url="http://localhost:8000")
    student = login(student_client, "student")
    assert student["courses"] == []


def test_title_match_does_not_cross_terms(tmp_path: Path) -> None:
    app = _app(
        tmp_path,
        {
            "summer-student": [candidate("alma", "unit:summer", title="Term Course")],
            "winter-student": [
                candidate(
                    "alma",
                    "unit:winter",
                    title="Term Course",
                    term="Winter 2026",
                )
            ],
        },
    )
    owner_client = TestClient(app, base_url="http://localhost:8000")
    owner = _professor_login(app, owner_client, "term-owner")
    created = owner_client.post(
        "/admin/course-workspaces",
        headers=mutation_headers(owner),
        json={
            "course_title": "Term Course",
            "term": "Winter 2026",
            "target": "full-course",
            "access_policy": "tuebingen_enrolled",
        },
    )
    course_id = created.json()["course"]["id"]

    summer = login(TestClient(app, base_url="http://localhost:8000"), "summer-student")
    winter = login(TestClient(app, base_url="http://localhost:8000"), "winter-student")

    assert summer["courses"] == []
    assert [course["id"] for course in winter["courses"]] == [course_id]


def test_enrollment_refresh_does_not_deactivate_another_tenant(tmp_path: Path) -> None:
    app = _app(tmp_path, {})
    login(TestClient(app, base_url="http://localhost:8000"), "multi-tenant-student")
    with app.state.database.session() as session:
        identity = session.scalar(
            select(ExternalIdentityRecord).where(
                ExternalIdentityRecord.subject == "multi-tenant-student"
            )
        )
        courses = [
            CourseRecord(
                tenant_id=tenant_id,
                owner_user_id=identity.user_id,
                title=f"Course {tenant_id}",
                term="Sommer 2026",
                access_policy="tuebingen_enrolled",
            )
            for tenant_id in ("tenant-a", "tenant-b")
        ]
        session.add_all(courses)
        session.flush()
        enrollments = [
            CourseEnrollmentRecord(
                course_id=course.id,
                user_id=identity.user_id,
                source="alma",
                external_course_id=f"unit:{index}",
                status="active",
            )
            for index, course in enumerate(courses, start=1)
        ]
        session.add_all(enrollments)
        session.flush()

        sync_external_courses(
            session,
            user_id=identity.user_id,
            tenant_id="tenant-a",
            observations=[],
            checked_sources={"alma"},
        )
        session.flush()

        assert enrollments[0].status == "inactive"
        assert enrollments[1].status == "active"


def test_login_loading_state_revokes_stale_external_access_until_fresh_sync(
    tmp_path: Path,
) -> None:
    external_course = candidate("alma", "unit:secure", title="Secure Systems")
    app = _app(tmp_path, {"student": [external_course]})
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
    assert created.status_code == 200
    login(TestClient(app, base_url="http://localhost:8000"), "student")

    repository = IdentityRepository(app.state.database)
    initial = UniversityLoginResult(
        username="student",
        term="Sommer 2026",
        alma_current_role="student",
        alma_available_roles=["student"],
    )
    loading = repository.begin_login(initial, tenant_id="tenant-tuebingen", sync_id="fresh")

    assert loading.university_course_sync_status == "loading"
    assert loading.courses == ()
    assert not repository.complete_course_sync(
        initial.model_copy(
            update={
                "courses": [external_course],
                "sources_checked": {ExternalCourseSource.ALMA},
            }
        ),
        tenant_id="tenant-tuebingen",
        sync_id="stale",
    )
    assert repository.complete_course_sync(
        initial.model_copy(
            update={
                "courses": [external_course],
                "sources_checked": {ExternalCourseSource.ALMA},
            }
        ),
        tenant_id="tenant-tuebingen",
        sync_id="fresh",
    )
    refreshed = repository.account(user_id=loading.user_id, tenant_id="tenant-tuebingen")
    assert refreshed is not None
    assert refreshed.university_course_sync_status == "ready"
    assert [course.id for course in refreshed.courses] == [created.json()["course"]["id"]]


def _app(tmp_path: Path, courses_by_user: dict) -> object:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    app.state.tuebingen_adapter = FakeUniversityAdapter(courses_by_user)
    return app


def _professor_login(app, client: TestClient, username: str) -> dict:
    app.state.tuebingen_adapter.roles_by_user[username] = "lecturer"
    return login(client, username)
