from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.models import Course, TuebingenLoginResult
from lecturepilot.tuebingen_adapter import TuebingenIntegrationUnavailable


def test_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_tuebingen_login_returns_courses_without_echoing_password() -> None:
    app = create_app()
    app.state.tuebingen_adapter = _FakeTuebingenAdapter()
    client = TestClient(app)

    response = client.post(
        "/auth/login",
        json={
            "username": "student01",
            "password": "very-secret-password",
            "term": "Sommer 2026",
        },
    )

    assert response.status_code == 200
    assert "very-secret-password" not in response.text
    assert response.json() == {
        "username": "student01",
        "term": "Sommer 2026",
        "courses": [
            {
                "id": "alma-machine-learning",
                "title": "Machine Learning",
                "professor": "Department of Computer Science",
                "term": "Sommer 2026",
            }
        ],
    }


def test_tuebingen_login_reports_missing_wrapper_dependency() -> None:
    app = create_app()
    app.state.tuebingen_adapter = _UnavailableTuebingenAdapter()
    client = TestClient(app)

    response = client.post(
        "/auth/login",
        json={
            "username": "student01",
            "password": "secret",
            "term": "Sommer 2026",
        },
    )

    assert response.status_code == 503
    assert "tue-api-wrapper" in response.json()["detail"]


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


def test_agent_turn_focuses_learning_goals(monkeypatch) -> None:
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
            "message": "What are the learning goals for this lecture?",
            "canvas_state": {"focused_section_id": "feature-maps"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["canvas_commands"][0]["section_id"] == "learning-goals"
    assert "learning goals" in payload["message"].lower()


def test_agent_turn_focuses_skill_check(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("LECTUREPILOT_MODEL", "openrouter/z-ai/glm-5.1")
    client = TestClient(create_app())

    response = client.post(
        "/agent/turn",
        json={
            "user_id": "u1",
            "course_id": "c1",
            "lecture_id": "l1",
            "attendance": "present",
            "message": "Test whether I understood the skill goals.",
            "canvas_state": {"focused_section_id": "kernel-trick"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["canvas_commands"][0]["section_id"] == "skill-check"
    assert "answer this" in payload["message"].lower()


class _FakeTuebingenAdapter:
    def login(self, *, username: str, password: str, term: str) -> TuebingenLoginResult:
        assert password == "very-secret-password"
        return TuebingenLoginResult(
            username=username,
            term=term,
            courses=[
                Course(
                    id="alma-machine-learning",
                    title="Machine Learning",
                    professor="Department of Computer Science",
                    term=term,
                )
            ],
        )


class _UnavailableTuebingenAdapter:
    def login(self, *, username: str, password: str, term: str) -> TuebingenLoginResult:
        raise TuebingenIntegrationUnavailable("tue-api-wrapper is not installed.")
