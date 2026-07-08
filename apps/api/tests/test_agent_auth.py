from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.models import TenantRole
from lecturepilot.providers import DEFAULT_MODEL
from lecturepilot.session_auth import sign_session
from lecturepilot.tenancy import TenantContext
from auth_helpers import student_headers


def test_production_auth_accepts_signed_session_token(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_AUTH_MODE", "session")
    monkeypatch.setenv("LECTUREPILOT_SESSION_SECRET", "test-session-secret")
    client = TestClient(create_app())
    token = sign_session(
        TenantContext(
            tenant_id="tenant-tuebingen",
            user_id="student01",
            roles=frozenset({TenantRole.STUDENT}),
        )
    )

    response = client.get(
        "/courses/martius-ml/lectures/lecture-03/canvas/publication",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_production_auth_rejects_forged_role_headers(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_AUTH_MODE", "session")
    monkeypatch.setenv("LECTUREPILOT_SESSION_SECRET", "test-session-secret")
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
    assert "Bearer session token" in response.json()["detail"]


def test_production_auth_protects_course_listing(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_AUTH_MODE", "session")
    monkeypatch.setenv("LECTUREPILOT_SESSION_SECRET", "test-session-secret")
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
    assert "Bearer session token" in response.json()["detail"]


def test_agent_turn_requires_configured_provider(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LECTUREPILOT_MODEL", DEFAULT_MODEL)
    client = TestClient(create_app())

    response = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json=_turn_payload("u1"),
    )

    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]


def test_agent_turn_uses_requested_provider_configuration(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = TestClient(create_app())
    payload = _turn_payload("u1")
    payload["model"] = "openrouter/openai/gpt-oss-120b:nitro"

    response = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json=payload,
    )

    assert response.status_code == 503
    assert "OPENROUTER_API_KEY" in response.json()["detail"]


def test_agent_turn_requires_authenticated_headers() -> None:
    client = TestClient(create_app())

    response = client.post("/agent/turn", json=_turn_payload("u1"))

    assert response.status_code == 401


def test_agent_turn_denies_learner_impersonation() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json=_turn_payload("u2"),
    )

    assert response.status_code == 403


def _turn_payload(user_id: str) -> dict:
    return {
        "user_id": user_id,
        "course_id": "c1",
        "lecture_id": "l1",
        "attendance": "present",
        "message": "Explain this section.",
        "canvas_state": {"focused_section_id": "intro"},
    }
