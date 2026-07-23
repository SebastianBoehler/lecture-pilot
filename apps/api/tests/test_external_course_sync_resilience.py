from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from lecturepilot import external_course_sync
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.db_models import (
    CourseEnrollmentRecord,
    CourseExternalRefRecord,
    ExternalIdentityRecord,
)
from security_db_helpers import FakeUniversityAdapter, candidate, login, mutation_headers


def test_one_course_mapping_conflict_does_not_block_other_courses(
    tmp_path: Path,
    monkeypatch,
) -> None:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    app.state.tuebingen_adapter = FakeUniversityAdapter({})
    owner_client = TestClient(app, base_url="http://localhost:8000")
    app.state.tuebingen_adapter.roles_by_user["owner"] = "lecturer"
    owner = login(owner_client, "owner")
    bad_course_id = _create_course(owner_client, owner, "Conflicting Course")
    good_course_id = _create_course(owner_client, owner, "Working Course")
    login(TestClient(app, base_url="http://localhost:8000"), "student")
    bad = candidate("alma", "unit:conflict", title="Conflicting Course")
    good = candidate("alma", "unit:working", title="Working Course")

    with app.state.database.session() as session:
        identity = session.scalar(
            select(ExternalIdentityRecord).where(ExternalIdentityRecord.subject == "student")
        )
        assert identity is not None
        session.add(
            CourseExternalRefRecord(
                course_id=UUID(bad_course_id),
                tenant_id="tenant-tuebingen",
                source=bad.source.value,
                external_course_id=bad.external_course_id,
                term=bad.term,
                title=bad.title,
            )
        )

    original_lookup = external_course_sync._external_course_ref

    def miss_conflicting_ref(session, tenant_id, observation):
        if observation.external_course_id == bad.external_course_id:
            return None
        return original_lookup(session, tenant_id, observation)

    monkeypatch.setattr(external_course_sync, "_external_course_ref", miss_conflicting_ref)
    with app.state.database.session() as session:
        identity = session.scalar(
            select(ExternalIdentityRecord).where(ExternalIdentityRecord.subject == "student")
        )
        external_course_sync.sync_external_courses(
            session,
            user_id=identity.user_id,
            tenant_id="tenant-tuebingen",
            observations=[bad, good],
            checked_sources={"alma"},
        )

    with app.state.database.session() as session:
        enrollment = session.scalar(
            select(CourseEnrollmentRecord).where(
                CourseEnrollmentRecord.course_id == UUID(good_course_id),
                CourseEnrollmentRecord.external_course_id == good.external_course_id,
            )
        )
        assert enrollment is not None
        assert enrollment.status == "active"


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
