import json
from typing import Literal

import pytest
from jsonschema import validate, ValidationError
from pydantic import BaseModel

from lecturepilot import agent_turn_orchestration
from lecturepilot.agent_response_schema import lecturepilot_response_format
from lecturepilot.coaching_transitions import derive_next_transition
from lecturepilot.model_payload import agent_result_from_content
from lecturepilot.practice_exam_latex import _safe_math, render_exam_markup
from lecturepilot.provider_json_schema import provider_json_schema
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.quality_gate_models import QualityGateStatus
from test_strict_model_payload import _gate, _payload, _turn
from test_strict_model_payload import _append_section_command


def test_plain_checkpoint_failure_keeps_an_independent_retry_available():
    transition = derive_next_transition(
        _gate(),
        current_stage="independent_exit",
        current_task_id="independent-exit",
        status=QualityGateStatus.NEEDS_EVIDENCE,
        exposed_hint_levels=[],
        exposed_task_ids=["independent-exit"],
    )
    assert not transition.support_exhausted
    assert transition.stage == "independent_exit"


def test_nullable_literal_schema_accepts_null_and_rejects_unknown_choices():
    class Choice(BaseModel):
        choice: Literal["chart", "table"] | None = None

    schema = provider_json_schema(Choice)
    validate({"choice": None}, schema)
    validate({"choice": "chart"}, schema)
    with pytest.raises(ValidationError):
        validate({"choice": "invented"}, schema)


def test_provider_canvas_schema_accepts_a_plain_paragraph_with_null_components():
    schema = lecturepilot_response_format(_turn())["json_schema"]["schema"]
    block_schema = schema["properties"]["canvas_commands"]["items"]["properties"]["section"][
        "properties"
    ]["blocks"]["items"]
    validate(_append_section_command()["section"]["blocks"][0], block_schema)


def test_chat_with_pending_check_cannot_assess():
    turn = _turn().model_copy(update={"checkpoint_gate_id": None})
    assert lecturepilot_response_format(turn)["json_schema"]["schema"]["properties"][
        "assessment"
    ] == {"type": "null"}
    payload = _payload()
    payload["assessment"]["evidence_ids"] = [item.id for item in _gate().evidence_criteria]
    payload["assessment"]["evidence_quotes"] = []
    with pytest.raises(ProviderConfigurationError, match="checkpoint"):
        agent_result_from_content(json.dumps(payload), turn, "model")


@pytest.mark.parametrize("error", [ValueError("private stale canvas"), OSError("private path")])
async def test_stream_reports_unexpected_errors_without_exposing_private_details(
    monkeypatch, error
):
    async def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(agent_turn_orchestration, "complete_agent_turn", fail)
    events = [
        json.loads(line)
        async for line in agent_turn_orchestration.agent_turn_events(None, turn=_turn())
    ]
    assert events[-1]["type"] == "error"
    assert "private" not in events[-1]["message"]


@pytest.mark.parametrize("expression", ["^^5cinput{x}", "^^^^005cinput{x}", "^^M\\input{x}"])
def test_tex_character_substitution_cannot_create_commands(expression):
    assert not _safe_math(expression)
    rendered = render_exam_markup(f"${expression}$")
    assert expression not in rendered
