from datetime import date
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from lecturepilot.app import create_app
from lecturepilot.canvas.canvas_workspace import CanvasWorkspace
from lecturepilot.core.db_models import (
    AuditEventRecord,
    CourseEnrollmentRecord,
    CourseExternalRefRecord,
    CourseRecord,
    ExternalIdentityRecord,
    UsageCounterRecord,
)
from security_db_helpers import (
    LegacyUniversityAccounts,
    candidate,
    login,
    mutation_headers,
    seed_course_ref,
)


def test_professor_delete_purges_course_database_and_workspace_state(tmp_path: Path) -> None:
    upstream = candidate("alma", "unit:delete", title="Delete Me")
    app = _app(tmp_path, {"student": [upstream]})
    owner_client = TestClient(app, base_url="http://localhost:8000")
    owner = _professor_login(app, owner_client, "owner")
    course_id = _create_course(owner_client, owner, "Delete Me")
    seed_course_ref(app.state.database, course_id, upstream)
    login(TestClient(app, base_url="http://localhost:8000"), "student")
    user_id = _identity_user_id(app, "student")
    learner_root = app.state.canvas_workspace.layout.user_course_root(str(user_id), course_id)
    learner_root.mkdir(parents=True)
    (learner_root / "notes.md").write_text("private learner note", encoding="utf-8")
    with app.state.database.session() as session:
        assert session.scalar(select(func.count()).select_from(CourseEnrollmentRecord)) == 1
        session.add(
            UsageCounterRecord(
                tenant_id="tenant-tuebingen",
                user_id=user_id,
                course_id=course_id,
                usage_date=date.today(),
            )
        )

    response = owner_client.delete(
        f"/admin/courses/{course_id}",
        headers=mutation_headers(owner),
    )

    assert response.status_code == 200
    assert response.json() == {"course_id": course_id, "deleted": True}
    assert not app.state.canvas_workspace.layout.course_root(course_id).exists()
    assert not learner_root.exists()
    with app.state.database.session() as session:
        assert session.get(CourseRecord, UUID(course_id)) is None
        assert session.scalar(select(func.count()).select_from(CourseExternalRefRecord)) == 0
        assert session.scalar(select(func.count()).select_from(CourseEnrollmentRecord)) == 0
        assert session.scalar(select(func.count()).select_from(UsageCounterRecord)) == 0
        event = session.scalar(
            select(AuditEventRecord).where(
                AuditEventRecord.event_type == "course.deleted",
                AuditEventRecord.target_id == course_id,
            )
        )
        assert event is not None


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


def _create_course(client: TestClient, owner: dict, title: str) -> str:
    response = client.post(
        "/admin/course-workspaces",
        headers=mutation_headers(owner),
        json={
            "course_title": title,
            "target": "full-course",
            "access_policy": "tuebingen_enrolled",
        },
    )
    assert response.status_code == 200, response.json()
    return response.json()["course"]["id"]


def _identity_user_id(app, subject: str) -> UUID:
    with app.state.database.session() as session:
        identity = session.scalar(
            select(ExternalIdentityRecord).where(ExternalIdentityRecord.subject == subject)
        )
        assert identity is not None
        return identity.user_id
