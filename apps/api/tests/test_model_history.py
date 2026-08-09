import json
import sys
from types import SimpleNamespace

import pytest

from lecturepilot.model_client import LiteLLMModelClient
from lecturepilot.models import AgentTurnInput, ProviderSettings


async def test_model_client_includes_server_owned_history_in_chronological_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        content = json.dumps(
            {
                "message": "The held-out set prevents optimistic evaluation.",
                "session_goal": None,
                "canvas_commands": [],
                "quality_gate": None,
            }
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))
    turn = AgentTurnInput.model_validate(
        {
            "user_id": "u1",
            "course_id": "course-1",
            "lecture_id": "lecture-01",
            "attendance": "present",
            "message": "Why was my last step wrong?",
            "recent_messages": [
                {"role": "user", "content": "I would evaluate on the training set."},
                {"role": "assistant", "content": "That would leak training information."},
            ],
        }
    )
    await LiteLLMModelClient().complete_turn(
        settings=ProviderSettings(
            provider="gemini",
            model="gemini/test-model",
            api_key_env="GEMINI_API_KEY",
            capabilities=set(),
        ),
        turn=turn,
    )

    messages = calls[0]["messages"]
    assert [message["role"] for message in messages] == ["system", "user", "assistant", "user"]
    assert messages[1]["content"] == "I would evaluate on the training set."
    assert messages[2]["content"] == "That would leak training information."
    assert messages[3]["content"].endswith("Student message: Why was my last step wrong?")
