from lecturepilot.agent_response_schema import lecturepilot_response_format
from test_strict_model_payload import _turn


def test_provider_navigation_ids_are_bounded_to_the_actual_canvas():
    schema = lecturepilot_response_format(_turn())["json_schema"]["schema"]
    command = schema["properties"]["canvas_commands"]["items"]["properties"]
    assert command["section_id"]["enum"] == [None, "mechanism"]
    assert command["span_id"]["enum"] == [None, "mechanism-text"]
    assert "mechanism-check" not in command["section_id"]["enum"]


def test_missing_canvas_cannot_provide_navigation_ids():
    turn = _turn().model_copy(update={"canvas_context": None})
    schema = lecturepilot_response_format(turn)["json_schema"]["schema"]
    command = schema["properties"]["canvas_commands"]["items"]["properties"]
    assert command["section_id"]["enum"] == [None]
    assert command["span_id"]["enum"] == [None]


def test_provider_text_limits_match_the_parser_contract():
    schema = lecturepilot_response_format(_turn())["json_schema"]["schema"]["properties"]
    command = schema["canvas_commands"]["items"]["properties"]
    assert command["highlight_text"]["maxLength"] == 160
    assert schema["session_goal"]["maxLength"] == 500
    assert schema["message"]["minLength"] == 1
    assert schema["assessment"]["properties"]["reason"]["maxLength"] == 500
