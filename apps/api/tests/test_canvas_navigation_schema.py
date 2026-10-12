import json

import pytest

from lecturepilot.agent_response_schema import lecturepilot_response_format
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.model_payload import agent_result_from_content
from lecturepilot.providers import ProviderConfigurationError
from test_strict_model_payload import _payload, _turn


def _chat_turn(*, learner_section: bool = False):
    turn = _turn(bound_check=False)
    if not learner_section:
        return turn
    note = CanvasSection(
        id="my-note",
        title="My note",
        blocks=[CanvasBlock(id="my-note-text", type="paragraph", text="Own words.")],
    )
    canvas = turn.canvas_context.model_copy(
        update={"sections": [*turn.canvas_context.sections, note]}
    )
    return turn.model_copy(update={"canvas_context": canvas, "learner_section_ids": ["my-note"]})


def _chat_payload(section_id: str, span_id: str) -> str:
    payload = _payload()
    payload["assessment"] = None
    payload["canvas_commands"][0]["section_id"] = section_id
    payload["canvas_commands"][1]["section_id"] = section_id
    payload["canvas_commands"][1]["span_id"] = span_id
    return json.dumps(payload)


def test_response_schema_is_identical_for_learners_with_different_canvases():
    plain = lecturepilot_response_format(_chat_turn())
    personal = lecturepilot_response_format(_chat_turn(learner_section=True))
    assert json.dumps(plain, sort_keys=True) == json.dumps(personal, sort_keys=True)
    command = plain["json_schema"]["schema"]["properties"]["canvas_commands"]["items"]
    assert "enum" not in command["properties"]["section_id"]
    assert command["properties"]["span_id"]["maxLength"] == 120


@pytest.mark.parametrize(
    ("section_id", "span_id"),
    [("invented", "mechanism-text"), ("mechanism", "invented-span"), ("my-note", "my-note-text")],
)
def test_navigation_ids_outside_the_turn_canvas_still_fail_closed(section_id, span_id):
    with pytest.raises(ProviderConfigurationError):
        agent_result_from_content(_chat_payload(section_id, span_id), _chat_turn(), "openai/x")


def test_learner_owned_sections_remain_valid_navigation_targets():
    result = agent_result_from_content(
        _chat_payload("my-note", "my-note-text"), _chat_turn(learner_section=True), "openai/x"
    )
    assert [command.section_id for command in result.canvas_commands] == ["my-note", "my-note"]


def test_provider_text_limits_match_the_parser_contract():
    schema = lecturepilot_response_format(_turn())["json_schema"]["schema"]["properties"]
    command = schema["canvas_commands"]["items"]["properties"]
    assert command["highlight_text"]["maxLength"] == 160
    assert schema["session_goal"]["maxLength"] == 500
    assert schema["message"]["minLength"] == 1
    assert schema["assessment"]["properties"]["reason"]["maxLength"] == 500
