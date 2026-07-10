from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from canvas_workspace_fixtures import write_course_source
from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.agent_tool_loop import complete_tool_turn
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.gate_policy import keep_canvas_actions_from_passing_gate
from lecturepilot.models import AgentTurnInput, AgentTurnResult, ProviderSettings, QualityGateDecision, QualityGateStatus
from lecturepilot.observability import Observability
from lecturepilot.providers import DEFAULT_MODEL
from auth_helpers import student_headers


def test_unix_named_tools_search_read_and_write_canvas(tmp_path) -> None:
    workspace = _workspace(tmp_path)
    workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
    executor = AgentToolExecutor(
        canvas_workspace=workspace,
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="u1",
    )

    assert executor.execute("ls", {"path": "/"})["entries"]
    matches = executor.execute("grep", {"path": "/lecture/canvas", "pattern": "Bayes"})
    assert matches["ok"] is True
    assert matches["matches"]

    result = executor.execute(
        "write",
        {
            "path": "/lecture/canvas/student/loss-note.md",
            "content": (
                "---\n"
                'id: "student-loss-note"\n'
                'title: "Loss note"\n'
                'source_ref: "student workspace"\n'
                "---\n\n"
                '<!-- block id="student-loss-note-p-1" type="paragraph" -->\n'
                "Loss functions change which decision is rational.\n"
            ),
        },
    )

    assert result["ok"] is True
    assert result["path"] == "/lecture/canvas/student/90-loss-note.md"
    commands = executor.canvas_update_commands()
    assert commands[0].type == "update_section"
    assert commands[0].section_id == "student-loss-note"
    plain = executor.execute(
        "write",
        {
            "path": "/lecture/canvas/student/plain-threshold-note.md",
            "content": "# Plain threshold note\n\nLoss thresholds shift the rational decision boundary.",
        },
    )
    assert plain["ok"] is True
    assert plain["path"] == "/lecture/canvas/student/91-plain-threshold-note.md"
    assert plain["section_id"] == "plain-threshold-note-md"
    section_ids = {command.section_id for command in executor.canvas_update_commands()}
    assert "plain-threshold-note-md" in section_ids
    plain_section = workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1").sections[-1]
    assert plain_section.title == "Plain threshold note"
    assert "# Plain threshold note" not in plain_section.blocks[0].text
    assert executor.canvas_update_commands()[-1].section_id == "plain-threshold-note-md"
    highlighted = executor.execute(
        "highlight",
        {
            "span_id": "plain-threshold-note-md-paragraph-1",
            "highlight_text": "Loss thresholds shift the rational decision boundary.",
        },
    )
    assert highlighted["ok"] is True
    assert highlighted["span_id"] != "plain-threshold-note-md-paragraph-1"

    denied = executor.execute("write", {"path": "/course/materials/x.md", "content": "no"})
    assert denied == {"ok": False, "error": "Path is outside the workspace capability."}


def test_agent_route_merges_low_level_canvas_write(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_OBSERVABILITY", "none")
    app = create_app()
    app.state.canvas_workspace = _workspace(tmp_path)
    app.state.agent_harness = _ToolWritingHarness()
    client = TestClient(app)

    response = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json={
            "course_id": "martius-ml",
            "lecture_id": "lecture-03",
            "attendance": "absent",
            "message": "append a loss note",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["canvas_commands"][0]["section_id"] == "student-tool-note"
    assert payload["canvas_commands"][0]["section"]["title"] == "Tool note"
    assert payload["canvas_commands"][-1]["type"] == "focus_section"
    assert payload["canvas_commands"][-1]["section_id"] == "student-tool-note"


async def test_tool_loop_executes_grep_before_final_answer(tmp_path) -> None:
    workspace = _workspace(tmp_path)
    workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
    executor = AgentToolExecutor(
        canvas_workspace=workspace,
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="u1",
    )
    calls: list[dict[str, Any]] = []

    async def fake_completion(**kwargs):
        calls.append(_snapshot_call(kwargs))
        if len(calls) == 1:
            return _response(
                tool_calls=[
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {
                            "name": "grep",
                            "arguments": json.dumps({"path": "/lecture/canvas", "pattern": "Bayes"}),
                        },
                    }
                ]
            )
        return _response(
            content=json.dumps(
                {
                    "message": "I checked the canvas with grep before answering.",
                    "canvas_commands": [{"type": "focus_section", "section_id": "bayes-formula"}],
                    "quality_gate": {
                        "gate_id": "bayes-decision-check",
                        "status": "needs_evidence",
                        "reason": "Needs a worked explanation.",
                    },
                }
            )
        )

    result = await complete_tool_turn(
        acompletion=fake_completion,
        settings=ProviderSettings(
            provider="gemini",
            model=DEFAULT_MODEL,
            api_key_env="GEMINI_API_KEY",
            capabilities=set(),
        ),
        turn=AgentTurnInput(
            user_id="u1",
            course_id="martius-ml",
            lecture_id="lecture-03",
            attendance="absent",
            message="explain Bayes",
        ),
        tool_executor=executor,
        observability=Observability(),
        emit=None,
        messages=[{"role": "system", "content": "Return JSON."}, {"role": "user", "content": "Hi"}],
        tool_profile="evidence",
    )

    assert result.message.startswith("I checked")
    assert {schema["function"]["name"] for schema in calls[0]["tools"]}.issuperset({"grep", "find"})
    assert calls[1]["messages"][-1]["role"] == "tool"
    assert "Bayes" in calls[1]["messages"][-1]["content"]


async def test_tool_loop_recovers_from_empty_post_tool_message(tmp_path) -> None:
    workspace = _workspace(tmp_path)
    workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
    executor = AgentToolExecutor(
        canvas_workspace=workspace,
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="u1",
    )
    calls: list[dict[str, Any]] = []

    async def fake_completion(**kwargs):
        calls.append(_snapshot_call(kwargs))
        if len(calls) == 1:
            return _response(
                tool_calls=[
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {"name": "find", "arguments": json.dumps({"path": "/lecture/canvas"})},
                    }
                ]
            )
        if len(calls) == 2:
            return _response(content=None)
        return _response(
            content=json.dumps(
                {
                        "message": "Final JSON after empty tool response.",
                        "canvas_commands": [{"type": "focus_section", "section_id": "bayes-formula"}],
                        "quality_gate": {
                            "gate_id": "bayes-decision-check",
                            "status": "needs_evidence",
                            "reason": "Needs a worked explanation.",
                        },
                    }
                )
            )

    result = await complete_tool_turn(
        acompletion=fake_completion,
        settings=ProviderSettings(
            provider="gemini",
            model=DEFAULT_MODEL,
            api_key_env="GEMINI_API_KEY",
            capabilities=set(),
        ),
        turn=AgentTurnInput(
            user_id="u1",
            course_id="martius-ml",
            lecture_id="lecture-03",
            attendance="absent",
            message="find the canvas",
        ),
        tool_executor=executor,
        observability=Observability(),
        emit=None,
        messages=[{"role": "system", "content": "Return JSON."}, {"role": "user", "content": "Hi"}],
        tool_profile="evidence",
    )

    assert result.message == "Final JSON after empty tool response."
    assert "tools" not in calls[2]
    assert calls[2]["messages"][-1]["role"] == "user"
    assert "final LecturePilot JSON" in calls[2]["messages"][-1]["content"]


def test_canvas_edit_request_cannot_pass_quality_gate() -> None:
    result = AgentTurnResult(
        message="I added a section.",
        model=DEFAULT_MODEL,
        quality_gate=QualityGateDecision(
            gate_id="bayes-decision-check",
            status=QualityGateStatus.PASSED,
            reason="The student asked for a section.",
        ),
    )

    checked = keep_canvas_actions_from_passing_gate(result, "create a new section about loss")

    assert checked.quality_gate
    assert checked.quality_gate.status == QualityGateStatus.NOT_ASSESSED


class _ToolWritingHarness:
    async def run_turn(self, turn: AgentTurnInput, *, tool_executor, **kwargs) -> AgentTurnResult:
        tool_executor.execute(
            "write",
            {
                "path": "/lecture/canvas/student/tool-note.md",
                "content": (
                    "---\n"
                    'id: "student-tool-note"\n'
                    'title: "Tool note"\n'
                    'source_ref: "student workspace"\n'
                    "---\n\n"
                    '<!-- block id="student-tool-note-p-1" type="paragraph" -->\n'
                    "This was written through the low-level write tool.\n"
                ),
            },
        )
        return AgentTurnResult(message="Done through write.", model=DEFAULT_MODEL)


def _workspace(tmp_path) -> CanvasWorkspace:
    return CanvasWorkspace(workspace_root=tmp_path / "workspaces", material_root=write_course_source(tmp_path))


def _snapshot_call(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {**kwargs, "messages": [dict(message) for message in kwargs.get("messages", [])]}


def _response(content: str | None = None, tool_calls: list[dict] | None = None):
    return SimpleNamespace(
        choices=[SimpleNamespace(message={"role": "assistant", "content": content, "tool_calls": tool_calls or []})]
    )
