from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas.canvas_workspace import CanvasWorkspace
from security_db_helpers import LegacyUniversityAccounts, login, mutation_headers


def test_legacy_alma_nonstudent_role_keeps_professor_access(tmp_path: Path) -> None:
    client = _client(tmp_path, {"alma-professor": "lecturer"})

    professor = login(client, "alma-professor")

    assert professor["account_type"] == "professor"
    assert professor["email"] == "alma-professor@uni-tuebingen.de"
    assert professor["university_role"] == "lecturer"
    assert professor["roles"] == ["professor"]
    created = client.post(
        "/admin/course-workspaces",
        headers=mutation_headers(professor),
        json={"course_title": "Secure Computing", "target": "full-course"},
    )
    assert created.status_code == 200, created.json()


def test_legacy_alma_student_role_stays_student(tmp_path: Path) -> None:
    client = _client(tmp_path, {"alma-student": "student"})

    student = login(client, "alma-student")

    assert student["account_type"] == "student"
    assert student["university_role"] == "student"
    assert student["roles"] == ["student"]
    denied = client.post(
        "/admin/course-workspaces",
        headers=mutation_headers(student),
        json={"course_title": "Unauthorized course", "target": "full-course"},
    )
    assert denied.status_code == 403


def _client(tmp_path: Path, roles: dict[str, str]) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    app.state.legacy_accounts = LegacyUniversityAccounts({}, roles)
    return TestClient(app, base_url="http://localhost:8000")
