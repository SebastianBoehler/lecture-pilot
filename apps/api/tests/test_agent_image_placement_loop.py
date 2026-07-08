from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from canvas_workspace_fixtures import write_course_source
from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.agent_tool_loop import complete_tool_turn
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.image_generation import GeneratedImage
from lecturepilot.models import AgentTurnInput, ProviderSettings
from lecturepilot.observability import Observability
from lecturepilot.providers import DEFAULT_MODEL


async def test_tool_loop_requires_image_placement_before_final_answer(tmp_path) -> None:
    workspace = CanvasWorkspace(workspace_root=tmp_path / "workspaces", material_root=write_course_source(tmp_path))
    workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
    setup = AgentToolExecutor(canvas_workspace=workspace, course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
    written = setup.execute(
        "write",
        {
            "path": "/lecture/canvas/student/regression-tasks.md",
            "content": "# Regression Tasks\n\nRegression maps inputs to continuous targets.",
        },
    )
    executor = AgentToolExecutor(
        canvas_workspace=workspace,
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="u1",
        image_generator=_FakeImageGenerator(),
    )
    calls: list[dict[str, Any]] = []

    async def fake_completion(**kwargs):
        calls.append(_snapshot_call(kwargs))
        if len(calls) == 1:
            return _response(tool_calls=[_generate_image_call(written["section_id"])])
        if len(calls) == 2:
            return _response(content=_final_json("I added the visual."))
        if len(calls) == 3:
            generated = _latest_tool_json(kwargs["messages"])
            return _response(tool_calls=[_edit_image_call(written["path"], generated["markdown"])])
        return _response(content=_final_json("Now the visual is placed in the section."))

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
            message="explain this visually",
        ),
        tool_executor=executor,
        observability=Observability(),
        emit=None,
        messages=[{"role": "system", "content": "Return JSON."}, {"role": "user", "content": "Hi"}],
    )

    assert result.message == "Now the visual is placed in the section."
    assert calls[2]["messages"][-1]["role"] == "user"
    assert "not visible on the canvas yet" in calls[2]["messages"][-1]["content"]
    assert executor.pending_canvas_edit_instruction() is None


def _generate_image_call(section_id: str) -> dict[str, Any]:
    return {
        "id": "call-1",
        "type": "function",
        "function": {
            "name": "generate_image",
            "arguments": json.dumps(
                {
                    "prompt": "Show regression as inputs, model, loss, and output.",
                    "section_id": section_id,
                    "filename": "regression-visual",
                }
            ),
        },
    }


def _edit_image_call(path: str, markdown: str) -> dict[str, Any]:
    return {
        "id": "call-2",
        "type": "function",
        "function": {
            "name": "edit",
            "arguments": json.dumps(
                {
                    "path": path,
                    "old_text": "Regression maps inputs to continuous targets.",
                    "new_text": "Regression maps inputs to continuous targets.\n\n" + markdown,
                }
            ),
        },
    }


def _snapshot_call(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {**kwargs, "messages": [dict(message) for message in kwargs.get("messages", [])]}


def _latest_tool_json(messages: list[dict[str, Any]]) -> dict[str, Any]:
    for message in reversed(messages):
        if message.get("role") == "tool":
            return json.loads(message["content"])
    raise AssertionError("missing tool message")


def _final_json(message: str) -> str:
    return json.dumps(
        {
            "message": message,
            "canvas_commands": [],
            "quality_gate": {
                "gate_id": "visual-check",
                "status": "needs_evidence",
                "reason": "Needs learner explanation.",
            },
        }
    )


class _FakeImageGenerator:
    def generate_infographic(self, *, prompt, section):
        return GeneratedImage(
            content=b"fake-png",
            mime_type="image/png",
            extension="png",
            caption=f"Infographic for {section.id}",
            provider="fake",
            model="fake-image-model",
        )


def _response(content: str | None = None, tool_calls: list[dict] | None = None):
    return SimpleNamespace(
        choices=[SimpleNamespace(message={"role": "assistant", "content": content, "tool_calls": tool_calls or []})]
    )
