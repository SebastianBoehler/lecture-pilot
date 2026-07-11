from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.db_models import (
    ExternalIdentityRecord,
    ProfessorRequestRecord,
    TenantMembershipRecord,
)
from lecturepilot.university_models import UniversityLoginResult
from security_db_helpers import mutation_headers


def test_alma_nonstudent_role_creates_pending_professor_without_privileges(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path, {"alma-professor": "lecturer"})
    client = TestClient(app, base_url="http://localhost:8000")

    response = _login(client, "alma-professor")

    assert response["account_type"] == "professor"
    assert response["university_role"] == "lecturer"
    assert response["professor_status"] == "pending"
    assert response["roles"] == []
    denied = client.post(
        "/admin/course-workspaces",
        headers=mutation_headers(response),
        json={"course_title": "Unapproved course", "target": "full-course"},
    )
    assert denied.status_code == 403
    with app.state.database.session() as session:
        identity = _identity(session, "alma-professor")
        requests = session.scalars(
            select(ProfessorRequestRecord).where(
                ProfessorRequestRecord.user_id == identity.user_id,
            )
        ).all()
        assert identity.provider_claims["alma_current_role"] == "lecturer"
        assert len(requests) == 1


def test_admin_approval_unlocks_alma_professor_course_creation(tmp_path: Path) -> None:
    app = _app(tmp_path, {"alma-professor": "lecturer", "platform-admin": "student"})
    professor_client = TestClient(app, base_url="http://localhost:8000")
    pending_professor = _login(professor_client, "alma-professor")
    admin_client = TestClient(app, base_url="http://localhost:8000")
    _login(admin_client, "platform-admin")
    with app.state.database.session() as session:
        admin_identity = _identity(session, "platform-admin")
        membership = session.get(
            TenantMembershipRecord,
            (admin_identity.user_id, "tenant-tuebingen"),
        )
        membership.platform_admin = True
    admin = _login(admin_client, "platform-admin")

    requests = admin_client.get("/platform/professor-requests")
    assert requests.status_code == 200
    assert requests.json()[0]["university_role"] == "lecturer"
    approved = admin_client.post(
        f"/platform/professor-requests/{requests.json()[0]['id']}/approve",
        headers=mutation_headers(admin),
    )
    assert approved.status_code == 200
    assert professor_client.get("/me").status_code == 401

    professor = _login(professor_client, "alma-professor")
    assert professor["roles"] == ["professor"]
    created = professor_client.post(
        "/admin/course-workspaces",
        headers=mutation_headers(professor),
        json={
            "course_title": "Secure Computing",
            "term": "Winter 2026",
            "target": "full-course",
            "access_policy": "tuebingen_enrolled",
        },
    )
    assert created.status_code == 200, created.json()
    assert pending_professor["roles"] == []


def test_active_student_role_stays_student_even_with_other_available_roles(
    tmp_path: Path,
) -> None:
    app = _app(
        tmp_path,
        {"alma-student": "student"},
        available_roles={"alma-student": ["student", "lecturer"]},
    )
    response = _login(TestClient(app, base_url="http://localhost:8000"), "alma-student")

    assert response["account_type"] == "student"
    assert response["university_role"] == "student"
    assert response["professor_status"] == "not_requested"
    assert response["roles"] == ["student"]


def test_current_student_role_removes_previously_approved_professor_permission(
    tmp_path: Path,
) -> None:
    roles = {"role-change": "lecturer"}
    app = _app(tmp_path, roles)
    client = TestClient(app, base_url="http://localhost:8000")
    pending = _login(client, "role-change")
    with app.state.database.session() as session:
        identity = _identity(session, "role-change")
        membership = session.get(
            TenantMembershipRecord,
            (identity.user_id, "tenant-tuebingen"),
        )
        membership.professor_status = "approved"

    roles["role-change"] = "student"
    downgraded = _login(client, "role-change")

    assert downgraded["account_type"] == "student"
    assert downgraded["roles"] == ["student"]
    denied = client.post(
        "/admin/course-workspaces",
        headers=mutation_headers(downgraded),
        json={"course_title": "Downgraded course", "target": "full-course"},
    )
    assert denied.status_code == 403
    assert pending["roles"] == []


def _app(
    tmp_path: Path,
    roles: dict[str, str],
    *,
    available_roles: dict[str, list[str]] | None = None,
):
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    app.state.tuebingen_adapter = _RoleUniversityAdapter(roles, available_roles or {})
    return app


def _login(client: TestClient, username: str) -> dict:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": "university-password"},
    )
    assert response.status_code == 200, response.json()
    return response.json()


def _identity(session, username: str) -> ExternalIdentityRecord:
    return session.scalar(
        select(ExternalIdentityRecord).where(
            ExternalIdentityRecord.provider == "tuebingen",
            ExternalIdentityRecord.subject == username,
        )
    )


class _RoleUniversityAdapter:
    def __init__(
        self,
        roles: dict[str, str],
        available_roles: dict[str, list[str]],
    ) -> None:
        self.roles = roles
        self.available_roles = available_roles

    def login(self, *, username: str, password: str, term: str) -> UniversityLoginResult:
        assert password
        current_role = self.roles[username]
        return UniversityLoginResult(
            username=username,
            email=f"{username}@example.edu",
            term=term,
            alma_current_role=current_role,
            alma_available_roles=self.available_roles.get(username, [current_role]),
        )
