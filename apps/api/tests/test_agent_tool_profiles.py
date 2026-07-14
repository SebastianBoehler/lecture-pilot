from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from canvas_workspace_fixtures import write_course_source
from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.agent_tool_loop import complete_tool_turn
from lecturepilot.agent_tool_schemas import (
    agent_tool_names,
    agent_tool_schemas,
    tutor_tool_profile_for_message,
)
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.models import AgentTurnInput, ProviderSettings
from lecturepilot.observability import Observability
from lecturepilot.providers import DEFAULT_MODEL


def test_agent_tool_profiles_expose_minimal_expected_tools() -> None:
    tutor = agent_tool_names("tutor")
    evidence = agent_tool_names("evidence")
    course_builder = agent_tool_names("course_builder")

    assert {"find", "grep"}.isdisjoint(tutor)
    assert {"find", "grep"}.issubset(evidence)
    assert {"record_gate", "remember"}.issubset(tutor)
    assert {"record_gate", "remember", "focus", "highlight"}.isdisjoint(course_builder)
    assert {
        "pwd",
        "ls",
        "find",
        "grep",
        "read",
        "write",
        "edit",
        "generate_image",
    } == course_builder
    assert {schema["function"]["name"] for schema in agent_tool_schemas("tutor")} == tutor
    assert tutor_tool_profile_for_message("show me the exact source for this claim") == "evidence"
    assert tutor_tool_profile_for_message("help me understand this formula") == "tutor"


async def test_tool_loop_default_profile_rejects_search_tool_calls(tmp_path) -> None:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=write_course_source(tmp_path)
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
            return _response(
                tool_calls=[
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {
                            "name": "grep",
                            "arguments": json.dumps(
                                {"path": "/lecture/canvas", "pattern": "Bayes"}
                            ),
                        },
                    }
                ]
            )
        return _response(
            content=json.dumps(
                {
                    "message": "I continued without the disabled search tool.",
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
    )

    assert result.message.startswith("I continued")
    assert {schema["function"]["name"] for schema in calls[0]["tools"]}.isdisjoint({"grep", "find"})
    assert "not enabled" in calls[1]["messages"][-1]["content"]


def _response(content: str | None = None, tool_calls: list[dict] | None = None):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message={"role": "assistant", "content": content, "tool_calls": tool_calls or []}
            )
        ]
    )
