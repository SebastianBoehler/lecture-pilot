import json

import pytest

from lecturepilot.agent_response_schema import lecturepilot_response_format
from lecturepilot.model_payload import agent_result_from_content
from lecturepilot.providers import ProviderConfigurationError
from test_strict_model_payload import _payload, _turn


def test_server_derives_next_check_without_provider_copy() -> None:
    payload = _payload()
    payload.pop("next_check", None)
    turn = _turn()

    result = agent_result_from_content(json.dumps(payload), turn, "contract-model")

    assert result.quality_gate.status.value == "needs_evidence"
    assert result.next_check.prompt == turn.active_gate.prompt
    assert result.next_check.gate_revision == turn.active_gate.revision


def test_provider_schema_does_not_request_server_owned_next_check() -> None:
    schema = lecturepilot_response_format(_turn())["json_schema"]["schema"]

    assert "next_check" not in schema["properties"]
    assert "next_check" not in schema["required"]


def test_explicit_checkpoint_requires_assessment_even_for_incomplete_answer() -> None:
    turn = _turn()
    turn = turn.model_copy(
        update={"checkpoint_gate_id": turn.active_gate.id, "message": "I do not know yet."}
    )
    schema = lecturepilot_response_format(turn)["json_schema"]["schema"]
    assert schema["properties"]["assessment"]["type"] == "object"

    payload = _payload()
    payload.pop("next_check", None)
    payload["assessment"] = None
    with pytest.raises(ProviderConfigurationError, match="checkpoint.*assessment"):
        agent_result_from_content(json.dumps(payload), turn, "contract-model")


def test_non_answer_chat_can_keep_pending_check_without_assessment() -> None:
    payload = _payload()
    payload.pop("next_check", None)
    payload["assessment"] = None
    result = agent_result_from_content(json.dumps(payload), _turn(), "contract-model")

    assert result.quality_gate is None
    assert result.next_check is None
