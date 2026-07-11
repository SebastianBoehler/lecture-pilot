from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
    CanvasCommand,
)
from lecturepilot.providers import DEFAULT_MODEL
from lecturepilot.session_auth import SESSION_COOKIE_NAME
from lecturepilot.tuebingen_adapter import TuebingenIntegrationUnavailable
from lecturepilot.university_models import ExternalCourseCandidate, UniversityLoginResult
from auth_helpers import student_headers


def test_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_tuebingen_login_returns_courses_without_echoing_password(monkeypatch) -> None:
    monkeypatch.delenv("LECTUREPILOT_DEMO_INCLUDE_CREATED_COURSES", raising=False)
    app = create_app()
    app.state.tuebingen_adapter = _FakeTuebingenAdapter()
    client = TestClient(app)

    response = client.post(
        "/auth/login",
        json={
            "username": "student01",
            "password": "very-secret-password",
        },
    )

    assert response.status_code == 200
    assert "very-secret-password" not in response.text
    assert "httponly" in response.headers["set-cookie"].lower()
    assert SESSION_COOKIE_NAME in response.cookies
    payload = response.json()
    assert payload.pop("access_token") is None
    csrf_token = payload.pop("csrf_token")
    assert len(csrf_token) >= 32
    assert payload == {
        "username": "student01",
        "email": None,
        "term": "Sommer 2026",
        "tenant_id": "tenant-tuebingen",
        "account_type": "student",
        "university_role": None,
        "roles": ["student"],
        "professor_status": "not_requested",
        "courses": [],
        "university_courses": [
            {
                "source": "alma",
                "external_course_id": "unit:42",
                "term": "Sommer 2026",
                "title": "Machine Learning",
                "number": None,
                "organization": "Department of Computer Science",
                "instructor": None,
                "display_url": None,
            }
        ],
    }
    assert client.get("/me").json()["university_courses"] == payload["university_courses"]


def test_tuebingen_login_reports_missing_wrapper_dependency() -> None:
    app = create_app()
    app.state.tuebingen_adapter = _UnavailableTuebingenAdapter()
    client = TestClient(app)

    response = client.post(
        "/auth/login",
        json={
            "username": "student01",
            "password": "secret",
        },
    )

    assert response.status_code == 503
    assert "tue-api-wrapper" in response.json()["detail"]


def test_agent_turn_focuses_bayes_section(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("LECTUREPILOT_MODEL", DEFAULT_MODEL)
    app = create_app()
    app.state.agent_harness = _FakeHarness(
        message="A real model can answer this as a conversation.",
        section_id="bayes-formula",
    )
    client = TestClient(app)

    response = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json={
            "course_id": "martius-ml",
            "lecture_id": "lecture-01",
            "attendance": "absent",
            "message": "Can you explain Bayes formula?",
            "canvas_state": {"focused_section_id": "bayesian-decision-theory-the-aim"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == DEFAULT_MODEL
    assert payload["canvas_commands"][0] == {
        "type": "focus_section",
        "section_id": "bayes-formula",
        "span_id": None,
        "highlight_text": None,
        "artifact_id": None,
        "section": None,
        "placement": None,
    }
    assert "real model" in payload["message"].lower()


def test_agent_turn_focuses_learning_goals(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("LECTUREPILOT_MODEL", DEFAULT_MODEL)
    app = create_app()
    app.state.agent_harness = _FakeHarness(
        message="The Bayes formula section came from the model client.",
        section_id="bayes-formula",
    )
    client = TestClient(app)

    response = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json={
            "course_id": "martius-ml",
            "lecture_id": "lecture-01",
            "attendance": "absent",
            "message": "Explain Bayes formula from the lecture.",
            "canvas_state": {"focused_section_id": "bayesian-decision-theory-the-aim"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["canvas_commands"][0]["section_id"] == "bayes-formula"
    assert "model client" in payload["message"].lower()


def test_agent_turn_focuses_skill_check(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("LECTUREPILOT_MODEL", DEFAULT_MODEL)
    app = create_app()
    app.state.agent_harness = _FakeHarness(
        message="The model selected the skill check.",
        section_id="bayes-rule-to-sum-up",
    )
    client = TestClient(app)

    response = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json={
            "course_id": "martius-ml",
            "lecture_id": "lecture-01",
            "attendance": "present",
            "message": "Test whether I understood the Bayes decision rule.",
            "canvas_state": {"focused_section_id": "bayes-formula"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["canvas_commands"][0]["section_id"] == "bayes-rule-to-sum-up"
    assert "model selected" in payload["message"].lower()


def test_agent_turn_reports_model_execution_error(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("LECTUREPILOT_MODEL", DEFAULT_MODEL)
    app = create_app()
    app.state.agent_harness = _FailingHarness()
    client = TestClient(app)

    response = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json={
            "course_id": "martius-ml",
            "lecture_id": "lecture-01",
            "attendance": "present",
            "message": "hello",
            "canvas_state": {"focused_section_id": "bayes-formula"},
        },
    )

    assert response.status_code == 502
    assert "Model request failed" in response.json()["detail"]


def test_agent_turn_enriches_harness_with_canvas_context(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("LECTUREPILOT_MODEL", DEFAULT_MODEL)
    app = create_app()
    app.state.canvas_workspace = _FakeCanvasWorkspace()
    app.state.agent_harness = _ContextHarness()
    client = TestClient(app)

    response = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json={
            "course_id": "martius-ml",
            "lecture_id": "lecture-03",
            "attendance": "present",
            "message": "verify this",
            "canvas_state": {"focused_section_id": "bayes-formula"},
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Saw Bayesian Decision Theory."


class _FakeTuebingenAdapter:
    def login(self, *, username: str, password: str, term: str) -> UniversityLoginResult:
        assert password == "very-secret-password"
        return UniversityLoginResult(
            username=username,
            term=term,
            courses=[
                ExternalCourseCandidate(
                    source="alma",
                    external_course_id="unit:42",
                    title="Machine Learning",
                    organization="Department of Computer Science",
                    term=term,
                )
            ],
            sources_checked={"alma"},
        )


class _UnavailableTuebingenAdapter:
    def login(self, *, username: str, password: str, term: str) -> UniversityLoginResult:
        raise TuebingenIntegrationUnavailable("tue-api-wrapper is not installed.")


class _FakeHarness:
    def __init__(self, *, message: str, section_id: str) -> None:
        self.message = message
        self.section_id = section_id

    async def run_turn(self, turn: AgentTurnInput) -> AgentTurnResult:
        return AgentTurnResult(
            message=self.message,
            canvas_commands=[CanvasCommand(type="focus_section", section_id=self.section_id)],
            model=DEFAULT_MODEL,
        )


class _ContextHarness:
    async def run_turn(self, turn: AgentTurnInput) -> AgentTurnResult:
        assert turn.canvas_context is not None
        assert turn.canvas_context.title == "Bayesian Decision Theory"
        return AgentTurnResult(
            message="Saw Bayesian Decision Theory.",
            canvas_commands=[CanvasCommand(type="focus_section", section_id="bayes-formula")],
            model=DEFAULT_MODEL,
        )


class _FailingHarness:
    async def run_turn(self, turn: AgentTurnInput) -> AgentTurnResult:
        raise ModelExecutionError(
            "Model request failed. Check the provider key and model configuration."
        )


class _FakeCanvasWorkspace:
    def read_document(self, *, course_id: str, lecture_id: str, user_id: str) -> CanvasDocument:
        return CanvasDocument(
            id="martius-ml-lecture-03",
            course_id=course_id,
            lecture_id=lecture_id,
            title="Bayesian Decision Theory",
            source_kind="latex",
            source_ref="Lecture03-eng.tex",
            workspace_path=".lecturepilot/workspaces/test/canvas/index.md",
            sections=[CanvasSection(id="bayes-formula", title="Bayes formula")],
        )
