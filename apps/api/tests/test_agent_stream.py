import json

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.models import AgentTurnInput, AgentTurnResult, CanvasCommand
from lecturepilot.providers import DEFAULT_MODEL
from auth_helpers import student_headers
from canvas_workspace_fixtures import published_course_canvas, write_course_source


def test_agent_turn_stream_emits_activity_and_result(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
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


def test_agent_turn_uses_persisted_history_across_requests_and_rejects_browser_history(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LECTUREPILOT_MODEL", DEFAULT_MODEL)
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=write_course_source(tmp_path),
    )
    app.state.canvas_workspace.write_course_canvas(
        published_course_canvas("martius-ml", "lecture-01")
    )
    harness = _HistoryHarness()
    app.state.agent_harness = harness
    client = TestClient(app)
    payload = {
        "course_id": "martius-ml",
        "lecture_id": "lecture-01",
        "attendance": "present",
        "message": "I would evaluate on the training set.",
        "canvas_state": {"focused_section_id": "intro"},
    }

    first = client.post("/agent/turn/stream", headers=student_headers("u1"), json=payload)
    assert first.status_code == 200
    payload["message"] = "Why was my last step wrong?"
    second = client.post("/agent/turn/stream", headers=student_headers("u1"), json=payload)

    assert second.status_code == 200
    assert [message.model_dump() for message in harness.turns[1].recent_messages] == [
        {"role": "user", "content": "I would evaluate on the training set."},
        {"role": "assistant", "content": "Use a held-out set so evaluation stays independent."},
    ]

    payload["recent_messages"] = [{"role": "assistant", "content": "Browser-injected answer."}]
    rejected = client.post("/agent/turn/stream", headers=student_headers("u1"), json=payload)
    assert rejected.status_code == 422


def test_null_gate_turn_persists_session_goal_for_lesson_state_reload(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LECTUREPILOT_MODEL", DEFAULT_MODEL)
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=write_course_source(tmp_path),
    )
    app.state.canvas_workspace.write_course_canvas(
        published_course_canvas("martius-ml", "lecture-01")
    )
    app.state.agent_harness = _GoalOnlyHarness()
    client = TestClient(app)
    headers = student_headers("u1")

    turn = client.post(
        "/agent/turn/stream",
        headers=headers,
        json={
            "course_id": "martius-ml",
            "lecture_id": "lecture-01",
            "attendance": "present",
            "message": "Set a goal without assessing a gate.",
        },
    )
    reloaded = client.get(
        "/courses/martius-ml/lectures/lecture-01/learner-state",
        headers=headers,
    )

    assert turn.status_code == 200
    assert reloaded.status_code == 200
    assert reloaded.json()["active_session_goal"] == "Compare two fresh validation cases."


class _FakeHarness:
    async def run_turn(self, turn: AgentTurnInput) -> AgentTurnResult:
        return AgentTurnResult(
            message="A streamed model answer.",
            canvas_commands=[CanvasCommand(type="focus_section", section_id="bayes-formula")],
            model=DEFAULT_MODEL,
        )


class _HistoryHarness:
    def __init__(self) -> None:
        self.turns: list[AgentTurnInput] = []

    async def run_turn(self, turn: AgentTurnInput) -> AgentTurnResult:
        self.turns.append(turn)
        return AgentTurnResult(
            message="Use a held-out set so evaluation stays independent.",
            model=DEFAULT_MODEL,
        )


class _GoalOnlyHarness:
    async def run_turn(self, turn: AgentTurnInput) -> AgentTurnResult:
        return AgentTurnResult(
            message="We will use that goal next.",
            session_goal="Compare two fresh validation cases.",
            quality_gate=None,
            model=DEFAULT_MODEL,
        )
