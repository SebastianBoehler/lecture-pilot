from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from canvas_workspace_fixtures import write_course_source
from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.agent_tool_loop import complete_tool_turn
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.models import AgentTurnInput, ProviderSettings
from lecturepilot.observability import Observability
from lecturepilot.providers import DEFAULT_MODEL


async def test_tool_loop_repairs_plain_text_first_answer(tmp_path) -> None:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=write_course_source(tmp_path),
    )
    workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
    executor = AgentToolExecutor(
        canvas_workspace=workspace,
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="u1",
    )
    calls: list[dict[str, Any]] = []

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return _response(content="Supervised learning uses labeled input-output pairs.")
        return _response(
            content=json.dumps(
                {
                    "message": "Supervised learning uses labeled input-output pairs.",
                    "canvas_commands": [{"type": "focus_section", "section_id": "bayes-formula"}],
                    "quality_gate": {
                        "gate_id": "bayes-decision-check",
                        "status": "needs_evidence",
                        "reason": "Needs one worked example.",
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
            attendance="unknown",
            message="what is supervised learning",
        ),
        tool_executor=executor,
        observability=Observability(),
        emit=None,
        messages=[{"role": "system", "content": "Return JSON."}, {"role": "user", "content": "Hi"}],
        tool_profile="tutor",
    )

    assert result.message == "Supervised learning uses labeled input-output pairs."
    assert calls[0]["tool_choice"] == "auto"
    assert calls[1]["response_format"]["type"] == "json_schema"
    assert calls[1]["messages"][-2]["role"] == "assistant"
    assert calls[1]["messages"][-1]["content"].startswith("Return the final LecturePilot JSON")


def _response(content: str | None = None, tool_calls: list[dict] | None = None):
    return SimpleNamespace(
        choices=[SimpleNamespace(message={"role": "assistant", "content": content, "tool_calls": tool_calls or []})]
    )
