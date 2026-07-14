import json

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.models import AgentTurnInput, AgentTurnResult, CanvasCommand
from lecturepilot.providers import DEFAULT_MODEL
from auth_helpers import student_headers
from canvas_workspace_fixtures import published_course_canvas, write_course_source


def test_agent_turn_stream_emits_activity_and_result(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("LECTUREPILOT_MODEL", DEFAULT_MODEL)
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=write_course_source(tmp_path),
    )
    app.state.canvas_workspace.write_course_canvas(
        published_course_canvas("martius-ml", "lecture-01")
    )
    app.state.agent_harness = _FakeHarness()
    client = TestClient(app)

    response = client.post(
        "/agent/turn/stream",
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
    events = [json.loads(line) for line in response.text.splitlines()]
    activity_tags = [event["tag"] for event in events if event["type"] == "activity"]
    assert activity_tags == [
        "read canvas",
        "load learner memory",
        "save attendance",
        "load coaching progress",
        "call tutor model",
    ]
    assert events[-1]["type"] == "result"
    assert events[-1]["result"]["message"] == "A streamed model answer."


class _FakeHarness:
    async def run_turn(self, turn: AgentTurnInput) -> AgentTurnResult:
        return AgentTurnResult(
            message="A streamed model answer.",
            canvas_commands=[CanvasCommand(type="focus_section", section_id="bayes-formula")],
            model=DEFAULT_MODEL,
        )
