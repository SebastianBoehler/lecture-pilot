from fastapi.testclient import TestClient

from lecturepilot.app import create_app


def test_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_agent_turn_requires_configured_provider(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("LECTUREPILOT_MODEL", "openrouter/z-ai/glm-5.1")
    client = TestClient(create_app())

    response = client.post(
        "/agent/turn",
        json={
            "user_id": "u1",
            "course_id": "c1",
            "lecture_id": "l1",
            "attendance": "present",
            "message": "Explain this section.",
            "canvas_state": {"focused_section_id": "intro"},
        },
    )

    assert response.status_code == 503
    assert "OPENROUTER_API_KEY" in response.json()["detail"]


def test_agent_turn_focuses_kernel_section(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("LECTUREPILOT_MODEL", "openrouter/z-ai/glm-5.1")
    client = TestClient(create_app())

    response = client.post(
        "/agent/turn",
        json={
            "user_id": "u1",
            "course_id": "c1",
            "lecture_id": "l1",
            "attendance": "absent",
            "message": "Can you explain the kernel trick?",
            "canvas_state": {"focused_section_id": "feature-maps"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "openrouter/z-ai/glm-5.1"
    assert payload["canvas_commands"][0] == {
        "type": "focus_section",
        "section_id": "kernel-trick",
        "span_id": None,
        "artifact_id": None,
    }
    assert "kernel trick" in payload["message"].lower()
