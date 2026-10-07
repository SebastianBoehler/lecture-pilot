from lecturepilot.agent_response_schema import (
    lecturepilot_response_format,
    source_routing_response_format,
)
from lecturepilot.provider_json_schema import provider_json_schema
from lecturepilot.provider_turn_result import ProviderAgentTurnResult
from lecturepilot.provider_source_routes import SourceRoutingProposal
from test_strict_model_payload import _turn


def test_tutor_schema_uses_the_same_model_as_runtime_validation():
    expected = provider_json_schema(ProviderAgentTurnResult)
    actual = lecturepilot_response_format(_turn())["json_schema"]["schema"]
    assert actual["required"] == expected["required"]
    assert actual["properties"]["message"] == expected["properties"]["message"]
    assert (
        actual["properties"]["canvas_commands"]["items"]["required"]
        == expected["properties"]["canvas_commands"]["items"]["required"]
    )
    assert actual["properties"]["message"]["maxLength"] == 4000


def test_source_routing_schema_comes_from_its_boundary_model():
    assert source_routing_response_format()["json_schema"]["schema"] == provider_json_schema(
        SourceRoutingProposal
    )


def test_strict_schema_requires_even_nullable_defaulted_fields():
    def check(value):
        if isinstance(value, list):
            for item in value:
                check(item)
        if isinstance(value, dict):
            assert "$ref" not in value
            assert "default" not in value
            if "properties" in value:
                assert value["additionalProperties"] is False
                assert set(value["required"]) == set(value["properties"])
            for item in value.values():
                check(item)

    check(provider_json_schema(ProviderAgentTurnResult))
