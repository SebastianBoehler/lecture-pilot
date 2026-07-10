import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.identity_repository import IdentityRepository
from lecturepilot.university_models import UniversityLoginResult
from lecturepilot.providers import DEFAULT_MODEL
from lecturepilot.session_auth import SESSION_COOKIE_NAME
from auth_helpers import student_headers


def test_auth_defaults_fail_closed_without_local_env(monkeypatch) -> None:
    monkeypatch.delenv("LECTUREPILOT_ENV", raising=False)
    monkeypatch.delenv("LECTUREPILOT_AUTH_MODE", raising=False)
    client = TestClient(create_app())

    response = client.get(
        "/courses",
        headers={
            "X-Tenant-Id": "tenant-tuebingen",
            "X-User-Id": "student01",
            "X-User-Role": "student",
        },
    )

    assert response.status_code == 401
    assert "Session cookie or bearer token" in response.json()["detail"]


def test_production_env_rejects_dev_header_auth(monkeypatch) -> None:
    _require_database()
    monkeypatch.setenv("LECTUREPILOT_ENV", "production")
    monkeypatch.setenv("LECTUREPILOT_AUTH_MODE", "dev")
    monkeypatch.setenv("LECTUREPILOT_ALLOWED_HOSTS", "testserver")
    client = TestClient(create_app())

    response = client.get(
        "/courses",
        headers={
            "X-Tenant-Id": "tenant-tuebingen",
            "X-User-Id": "student01",
            "X-User-Role": "student",
        },
    )

    assert response.status_code == 500
    assert "Dev header auth requires" in response.json()["detail"]


def test_production_auth_accepts_opaque_session_token(monkeypatch, tmp_path) -> None:
    client, token, _csrf = _session_client(monkeypatch, tmp_path)

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["username"] == "student01"


def test_production_auth_accepts_session_cookie(monkeypatch, tmp_path) -> None:
    client, token, _csrf = _session_client(monkeypatch, tmp_path)

    client.cookies.set(SESSION_COOKIE_NAME, token)
    response = client.get("/me")

    assert response.status_code == 200


def test_local_dev_headers_ignore_stale_session_cookie(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LECTUREPILOT_ENV", "development")
    monkeypatch.setenv("LECTUREPILOT_AUTH_MODE", "dev")
    client = _client(tmp_path)
    client.cookies.set(SESSION_COOKIE_NAME, "stale-cookie")

    response = client.get(
        "/courses/martius-ml/lectures/lecture-03/canvas/publication",
        headers=student_headers("student01"),
    )

    assert response.status_code == 200


def test_me_requires_database_session_in_dev_mode(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LECTUREPILOT_ENV", "development")
    monkeypatch.setenv("LECTUREPILOT_AUTH_MODE", "dev")
    client = _client(tmp_path)

    response = client.get("/me", headers=student_headers("student01"))

    assert response.status_code == 401
    assert response.json()["detail"] == "Database session is required."


def test_production_auth_rejects_forged_role_headers(monkeypatch) -> None:
    _require_database()
    monkeypatch.setenv("LECTUREPILOT_ENV", "production")
    monkeypatch.setenv("LECTUREPILOT_AUTH_MODE", "session")
    monkeypatch.setenv("LECTUREPILOT_ALLOWED_HOSTS", "testserver")
    client = TestClient(create_app())

    response = client.post(
        "/agent/turn",
        headers={
            "X-Tenant-Id": "tenant-tuebingen",
            "X-User-Id": "student01",
            "X-User-Role": "professor",
        },
        json=_turn_payload("student01"),
    )

    assert response.status_code == 401
    assert "Session cookie or bearer token" in response.json()["detail"]


def test_production_auth_protects_course_listing(monkeypatch) -> None:
    _require_database()
    monkeypatch.setenv("LECTUREPILOT_ENV", "production")
    monkeypatch.setenv("LECTUREPILOT_AUTH_MODE", "session")
    monkeypatch.setenv("LECTUREPILOT_ALLOWED_HOSTS", "testserver")
    client = TestClient(create_app())

    response = client.get(
        "/courses",
        headers={
            "X-Tenant-Id": "tenant-tuebingen",
            "X-User-Id": "student01",
            "X-User-Role": "student",
        },
    )

    assert response.status_code == 401
    assert "Session cookie or bearer token" in response.json()["detail"]


def test_agent_turn_requires_configured_provider(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LECTUREPILOT_MODEL", DEFAULT_MODEL)
    client = _client(tmp_path)

    response = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json=_turn_payload("u1"),
    )

    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]


def test_agent_turn_rejects_browser_selected_model(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = _client(tmp_path)
    payload = _turn_payload("u1")
    payload["model"] = "openrouter/openai/gpt-oss-120b:nitro"

    response = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json=payload,
    )

    assert response.status_code == 422


def test_agent_turn_requires_authenticated_headers() -> None:
    client = TestClient(create_app())

    response = client.post("/agent/turn", json=_turn_payload("u1"))

    assert response.status_code == 401


def test_agent_turn_denies_learner_impersonation() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json={**_turn_payload("u2"), "user_id": "u2"},
    )

    assert response.status_code == 422


def _turn_payload(user_id: str) -> dict:
    return {
        "course_id": "martius-ml",
        "lecture_id": "lecture-03",
        "attendance": "present",
        "message": "Explain this section.",
        "canvas_state": {"focused_section_id": "intro"},
    }


def _client(tmp_path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    return TestClient(app)


def _session_client(monkeypatch, tmp_path) -> tuple[TestClient, str, str]:
    _require_database()
    monkeypatch.setenv("LECTUREPILOT_ENV", "production")
    monkeypatch.setenv("LECTUREPILOT_AUTH_MODE", "session")
    monkeypatch.setenv("LECTUREPILOT_ALLOWED_HOSTS", "lecturepilot.test")
    monkeypatch.setenv("LECTUREPILOT_ALLOWED_ORIGINS", "https://lecturepilot.test")
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    with app.state.database.session() as session:
        session.execute(
            text(
                "TRUNCATE usage_counters, audit_events, course_enrollments, "
                "course_external_refs, courses, external_course_observations, sessions, "
                "professor_requests, tenant_memberships, external_identities, users CASCADE"
            )
        )
    account = IdentityRepository(app.state.database).record_login(
        UniversityLoginResult(
            username="student01",
            term="Sommer 2026",
            courses=[],
            sources_checked=set(),
        ),
        tenant_id="tenant-tuebingen",
    )
    issued = app.state.session_store.create(account, ttl_minutes=60)
    return (
        TestClient(app, base_url="https://lecturepilot.test"),
        issued.token,
        issued.csrf_token,
    )


def _require_database() -> None:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("PostgreSQL test database is not configured.")
