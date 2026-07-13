from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.db_models import AuditEventRecord, ExternalIdentityRecord, UserRecord
from lecturepilot.university_models import UniversityLoginResult
from auth_helpers import pending_university_login
from security_db_helpers import mutation_headers


def test_alma_nonstudent_role_immediately_grants_professor_access_and_is_audited(
    tmp_path: Path,
) -> None:
    app = _app(
        tmp_path,
        {"alma-professor": "lecturer"},
        available_roles={"alma-professor": ["lecturer", "examiner"]},
    )
    client = TestClient(app, base_url="http://localhost:8000")

    professor = _login(client, "alma-professor")

    assert professor["account_type"] == "professor"
    assert professor["display_name"] == "Alma Professor"
    assert professor["email"] == "alma-professor@example.edu"
    assert professor["university_role"] == "lecturer"
    assert professor["roles"] == ["professor"]
    assert "professor_status" not in professor
    created = client.post(
        "/admin/course-workspaces",
        headers=mutation_headers(professor),
        json={"course_title": "Secure Computing", "target": "full-course"},
    )
    assert created.status_code == 200, created.json()

    with app.state.database.session() as session:
        identity = _identity(session, "alma-professor")
        assert identity.provider_claims == {
            "alma_current_role": "lecturer",
            "alma_available_roles": ["lecturer", "examiner"],
        }
        login_event = session.scalar(
            select(AuditEventRecord).where(
                AuditEventRecord.actor_user_id == identity.user_id,
                AuditEventRecord.event_type == "auth.login",
            )
        )
        assert login_event is not None
        assert login_event.details["alma_role"] == "lecturer"
        assert login_event.details["alma_available_roles"] == ["lecturer", "examiner"]
        assert "email" not in login_event.details
        assert "display_name" not in login_event.details
        assert session.get(UserRecord, identity.user_id).display_name == "Alma Professor"


def test_active_student_role_stays_student_even_with_other_available_roles(
    tmp_path: Path,
) -> None:
    app = _app(
        tmp_path,
        {"alma-student": "student"},
        available_roles={"alma-student": ["student", "lecturer"]},
    )
    client = TestClient(app, base_url="http://localhost:8000")

    student = _login(client, "alma-student")

    assert student["account_type"] == "student"
    assert student["university_role"] == "student"
    assert student["roles"] == ["student"]
    denied = client.post(
        "/admin/course-workspaces",
        headers=mutation_headers(student),
        json={"course_title": "Unauthorized course", "target": "full-course"},
    )
    assert denied.status_code == 403


def test_current_student_role_removes_previous_professor_access(tmp_path: Path) -> None:
    roles = {"role-change": "lecturer"}
    app = _app(tmp_path, roles)
    client = TestClient(app, base_url="http://localhost:8000")
    professor = _login(client, "role-change")
    created = client.post(
        "/admin/course-workspaces",
        headers=mutation_headers(professor),
        json={"course_title": "Formerly owned course", "target": "full-course"},
    )
    assert created.status_code == 200

    roles["role-change"] = "student"
    student = _login(client, "role-change")

    assert student["account_type"] == "student"
    assert student["roles"] == ["student"]
    assert student["courses"] == []
    denied = client.post(
        "/admin/course-workspaces",
        headers=mutation_headers(student),
        json={"course_title": "Downgraded course", "target": "full-course"},
    )
    assert denied.status_code == 403


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

    def authenticate(self, *, username: str, password: str, term: str):
        assert password
        current_role = self.roles[username]
        return pending_university_login(
            UniversityLoginResult(
                username=username,
                display_name=username.replace("-", " ").title(),
                email=f"{username}@example.edu",
                term=term,
                alma_current_role=current_role,
                alma_available_roles=self.available_roles.get(username, [current_role]),
            )
        )
