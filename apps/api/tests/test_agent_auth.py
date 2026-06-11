from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.providers import DEFAULT_MODEL
from auth_helpers import student_headers


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
