from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select, text

from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.db_models import ExternalIdentityRecord, TenantMembershipRecord
from security_db_helpers import FakeUniversityAdapter, login, mutation_headers


PROFESSOR_PASSWORD = "correct horse battery staple"


def test_professor_registration_creates_pending_argon2_account(tmp_path: Path) -> None:
    app = _app(tmp_path)
    client = TestClient(app, base_url="http://localhost:8000")

    response = client.post(
        "/auth/professor/register",
        json={
            "display_name": "Professor Ada Lovelace",
            "email": "Ada.Lovelace@Example.edu",
            "password": PROFESSOR_PASSWORD,
        },
    )

    assert response.status_code == 201, response.json()
    assert "httponly" in response.headers["set-cookie"].lower()
    payload = response.json()
    assert payload["username"] == "Professor Ada Lovelace"
    assert payload["email"] == "ada.lovelace@example.edu"
    assert payload["account_type"] == "professor"
    assert payload["professor_status"] == "pending"
    assert payload["roles"] == []
    assert PROFESSOR_PASSWORD not in response.text

    with app.state.database.session() as session:
        password_hash = session.execute(
            text("SELECT password_hash FROM local_credentials")
        ).scalar_one()
        pending = session.execute(
            text("SELECT count(*) FROM professor_requests WHERE status = 'pending'")
        ).scalar_one()
    assert password_hash.startswith("$argon2id$")
    assert PROFESSOR_PASSWORD not in password_hash
    assert pending == 1


def test_admin_approval_unlocks_professor_course_creation(tmp_path: Path) -> None:
    app = _app(tmp_path)
    professor_client = TestClient(app, base_url="http://localhost:8000")
    _register(professor_client)

    admin_client = TestClient(app, base_url="http://localhost:8000")
    login(admin_client, "platform-admin")
    with app.state.database.session() as session:
        admin_identity = session.scalar(
            select(ExternalIdentityRecord).where(
                ExternalIdentityRecord.provider == "tuebingen",
                ExternalIdentityRecord.subject == "platform-admin",
            )
        )
        membership = session.get(
            TenantMembershipRecord,
            (admin_identity.user_id, "tenant-tuebingen"),
        )
        membership.platform_admin = True
    admin = login(admin_client, "platform-admin")

    pending = admin_client.get("/platform/professor-requests")
    assert pending.status_code == 200
    assert pending.json()[0]["username"] == "Professor Ada Lovelace"
    assert pending.json()[0]["email"] == "ada.lovelace@example.edu"

    approved = admin_client.post(
        f"/platform/professor-requests/{pending.json()[0]['id']}/approve",
        headers=mutation_headers(admin),
    )
    assert approved.status_code == 200
    assert professor_client.get("/me").status_code == 401

    signed_in = professor_client.post(
        "/auth/professor/login",
        json={"email": "ada.lovelace@example.edu", "password": PROFESSOR_PASSWORD},
    )
    assert signed_in.status_code == 200, signed_in.json()
    professor = signed_in.json()
    assert professor["roles"] == ["professor"]
    assert professor["professor_status"] == "approved"

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
    assert created.json()["course"]["title"] == "Secure Computing"
    assert [course["id"] for course in professor_client.get("/courses").json()] == [
        created.json()["course"]["id"]
    ]
    learner_reset = professor_client.post(
        f"/courses/{created.json()['course']['id']}/learner-workspace/reset",
        headers=mutation_headers(professor),
        json={"reset_canvas": True, "reset_course_memory": False, "reset_progress": False},
    )
    assert learner_reset.status_code == 403


def test_professor_credentials_fail_closed_and_do_not_echo_password(tmp_path: Path) -> None:
    app = _app(tmp_path)
    client = TestClient(app, base_url="http://localhost:8000")
    _register(client)

    duplicate = TestClient(app, base_url="http://localhost:8000").post(
        "/auth/professor/register",
        json={
            "display_name": "Different Name",
            "email": "ADA.LOVELACE@example.edu",
            "password": "another sufficiently long password",
        },
    )
    wrong_password = TestClient(app, base_url="http://localhost:8000").post(
        "/auth/professor/login",
        json={"email": "ada.lovelace@example.edu", "password": "wrong password value"},
    )
    short_password = TestClient(app, base_url="http://localhost:8000").post(
        "/auth/professor/register",
        json={
            "display_name": "Professor Short",
            "email": "short@example.edu",
            "password": "too-short",
        },
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Professor registration could not be completed."
    assert wrong_password.status_code == 401
    assert wrong_password.json()["detail"] == "Email or password is incorrect."
    assert "wrong password value" not in wrong_password.text
    assert short_password.status_code == 422


def _register(client: TestClient) -> dict:
    response = client.post(
        "/auth/professor/register",
        json={
            "display_name": "Professor Ada Lovelace",
            "email": "Ada.Lovelace@Example.edu",
            "password": PROFESSOR_PASSWORD,
        },
    )
    assert response.status_code == 201, response.json()
    return response.json()


def _app(tmp_path: Path):
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    app.state.tuebingen_adapter = FakeUniversityAdapter({})
    return app
