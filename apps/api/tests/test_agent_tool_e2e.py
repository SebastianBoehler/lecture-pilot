from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from canvas_workspace_fixtures import write_course_source
from lecturepilot.agent_tool_loop import complete_tool_turn
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.models import AgentTurnInput, AgentTurnResult, ProviderSettings
from lecturepilot.observability import Observability
from lecturepilot.providers import DEFAULT_MODEL
from auth_helpers import student_headers


def test_streamed_tool_turn_persists_canvas_memory_and_gate(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_OBSERVABILITY", "none")
    app = create_app()
    app.state.canvas_workspace = _published_workspace(tmp_path)
    app.state.agent_harness = _ToolLoopHarness()
    client = TestClient(app)

    response = client.post(
        "/agent/turn/stream",
        headers=student_headers("student01"),
        json={
            "user_id": "student01",
            "course_id": "martius-ml",
            "lecture_id": "lecture-03",
            "attendance": "absent",
            "message": "I connect posterior evidence with risk-sensitive decisions.",
            "canvas_state": {"focused_section_id": "bayesian-decision-theory-the-aim"},
        },
    )

    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines()]
    activity_tags = [event["tag"] for event in events if event["type"] == "activity"]
    assert "write: /lecture/canvas/student/tool-loop-note.md" in activity_tags
    assert "remember" in activity_tags
    assert "record_gate: tool-loop-gate" in activity_tags
    assert "focus: student-tool-loop-note" in activity_tags
    assert "highlight: student-tool-loop-note-p-1" in activity_tags
    result = events[-1]["result"]
    assert result["quality_gate"]["gate_id"] == "tool-loop-gate"
    assert result["quality_gate"]["status"] == "needs_evidence"
    assert any(command["section_id"] == "student-tool-loop-note" for command in result["canvas_commands"])

    layout = app.state.canvas_workspace.layout
    user_root = layout.user_root("student01")
    lecture_root = layout.user_lecture_root("student01", "martius-ml", "lecture-03")
    assert "soccer analogies" in (user_root / "memories" / "global.md").read_text(encoding="utf-8")
    assert json.loads((user_root / "memories" / "preferences.json").read_text())["analogy"] == "soccer"
    assert "tool-loop-gate" in (lecture_root / "gates.json").read_text(encoding="utf-8")

    canvas_response = client.get(
        "/courses/martius-ml/lectures/lecture-03/canvas",
        headers=student_headers("student01"),
        params={"user_id": "student01"},
    )
    assert canvas_response.status_code == 200, canvas_response.json()
    canvas = canvas_response.json()
    student_section = next(section for section in canvas["sections"] if section["id"] == "student-tool-loop-note")
    assert student_section["blocks"][0]["text"] == "This was written through the real write tool."

    second = client.post(
        "/agent/turn",
        headers=student_headers("student01"),
        json={
            "user_id": "student01",
            "course_id": "martius-ml",
            "lecture_id": "lecture-03",
            "attendance": "present",
            "message": "Continue.",
        },
    )

    assert second.status_code == 200
    assert second.json()["message"] == "Loaded durable soccer preference."
    assert app.state.agent_harness.seen_memory_preferences == {"analogy": "soccer"}


class _ToolLoopHarness:
    def __init__(self) -> None:
        self.calls = 0
        self.seen_memory_preferences: dict[str, Any] = {}

    async def run_turn(self, turn: AgentTurnInput, *, tool_executor, observability, emit) -> AgentTurnResult:
        self.calls += 1
        if self.calls == 2:
            self.seen_memory_preferences = dict(turn.user_memory.preferences)
            assert "soccer analogies" in turn.user_memory.global_notes
            return AgentTurnResult(message="Loaded durable soccer preference.", model=DEFAULT_MODEL)
        return await complete_tool_turn(
            acompletion=_ToolCallingModel(),
            settings=ProviderSettings(
                provider="gemini",
                model=DEFAULT_MODEL,
                api_key_env="GEMINI_API_KEY",
                capabilities=set(),
            ),
            turn=turn,
            tool_executor=tool_executor,
            observability=observability or Observability(),
            emit=emit,
            messages=[{"role": "system", "content": "Use tools."}, {"role": "user", "content": turn.message}],
        )


class _ToolCallingModel:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, **_kwargs):
        self.calls += 1
        if self.calls == 1:
            return _response(tool_calls=_tool_calls())
        return _response(
            content=json.dumps(
                {
                    "message": "I wrote the note, saved memory, and recorded the gate.",
                    "canvas_commands": [],
                    "quality_gate": {
                        "gate_id": "fallback-gate",
                        "status": "not_assessed",
                        "reason": "Tool output supplies the actual gate.",
                        "next_prompt": None,
                    },
                }
            )
        )


def _tool_calls() -> list[dict[str, Any]]:
    return [
        _tool_call(
            "write",
            {
                "path": "/lecture/canvas/student/tool-loop-note.md",
                "content": (
                    "---\n"
                    'id: "student-tool-loop-note"\n'
                    'title: "Tool loop note"\n'
                    'source_ref: "student workspace"\n'
                    "---\n\n"
                    '<!-- block id="student-tool-loop-note-p-1" type="paragraph" -->\n'
                    "This was written through the real write tool.\n"
                ),
            },
        ),
        _tool_call(
            "remember",
            {
                "note": "student prefers soccer analogies",
                "preference_key": "analogy",
                "preference_value": "soccer",
            },
        ),
        _tool_call(
            "record_gate",
            {
                "gate_id": "tool-loop-gate",
                "status": "needs_evidence",
                "reason": "Student needs one more worked risk example.",
                "next_prompt": "Compute one expected-risk comparison.",
            },
        ),
        _tool_call("focus", {"section_id": "student-tool-loop-note"}),
        _tool_call(
            "highlight",
            {
                "span_id": "student-tool-loop-note-p-1",
                "highlight_text": "real write tool",
            },
        ),
    ]


def _tool_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"call-{name}",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def _response(content: str | None = None, tool_calls: list[dict] | None = None):
    return SimpleNamespace(
        choices=[SimpleNamespace(message={"role": "assistant", "content": content, "tool_calls": tool_calls or []})]
    )


def _published_workspace(tmp_path: Path) -> CanvasWorkspace:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=write_course_source(tmp_path),
    )
    workspace.write_course_canvas(
        workspace.source_document(
            course_id="martius-ml",
            lecture_id="lecture-03",
            workspace_path=str(tmp_path / "published" / "index.md"),
        )
    )
    return workspace
