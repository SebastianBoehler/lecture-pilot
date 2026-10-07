from __future__ import annotations

from typing import Any

from lecturepilot.tutor_response_constraints import constrain_tutor_response
from lecturepilot.learning_map import LearningMapGate
from lecturepilot.model_commands import checkpoint_assessment_required
from lecturepilot.models import AgentTurnInput
from lecturepilot.provider_turn_schema import assessment_schema
from lecturepilot.provider_turn_result import ProviderAgentTurnResult
from lecturepilot.provider_source_routes import SourceRoutingProposal, SourceRoutingReview
from lecturepilot.provider_json_schema import provider_json_schema


def lecturepilot_response_format(turn: AgentTurnInput) -> dict[str, Any]:
    bound = checkpoint_assessment_required(turn)
    schema = _agent_turn_schema(
        assessment_gate=(turn.active_gate if bound else None),
        required_assessment=checkpoint_assessment_required(turn),
    )
    constrain_tutor_response(schema, turn)
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "lecturepilot_agent_turn",
            "strict": True,
            "schema": schema,
        },
    }


def lecture_schedule_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "lecturepilot_lecture_schedule",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "lectures": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "number": {"type": "string"},
                                "title": {"type": "string"},
                                "date": {"type": "string"},
                                "material_path": _nullable_string(
                                    "Source file path for this lecture."
                                ),
                            },
                            "required": ["number", "title", "date", "material_path"],
                        },
                    },
                },
                "required": ["lectures"],
            },
        },
    }


def source_routing_response_format() -> dict[str, Any]:
    return _routing_response_format("lecturepilot_source_routing", SourceRoutingProposal)


def source_routing_review_response_format() -> dict[str, Any]:
    return _routing_response_format("lecturepilot_source_routing_review", SourceRoutingReview)


def _routing_response_format(name, model):
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": provider_json_schema(model),
        },
    }


def _agent_turn_schema(
    *, assessment_gate: LearningMapGate | None, required_assessment: bool
) -> dict[str, Any]:
    schema = provider_json_schema(ProviderAgentTurnResult)
    schema["properties"]["assessment"] = assessment_schema(
        assessment_gate, required=required_assessment
    )
    return schema


def _nullable_string(description: str) -> dict[str, Any]:
    return {"type": ["string", "null"], "description": description}
