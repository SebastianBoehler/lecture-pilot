from __future__ import annotations

from typing import Any

from lecturepilot.coaching_assistance import next_check_assistance_schema
from lecturepilot.learning_map import LearningMapGate


def assessment_schema(gate: LearningMapGate | None) -> dict[str, Any]:
    if gate is None:
        return {"type": "null"}
    return _nullable(
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "gate_id": {"type": "string", "const": gate.id},
                "gate_revision": {"type": "string", "const": gate.revision},
                "reason": {"type": "string"},
                "evidence_ids": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [item.id for item in gate.evidence_criteria],
                    },
                    "maxItems": len(gate.evidence_criteria),
                },
            },
            "required": [
                "gate_id",
                "gate_revision",
                "reason",
                "evidence_ids",
            ],
        }
    )


def next_check_schema(gate: LearningMapGate | None) -> dict[str, Any]:
    if gate is None:
        return {"type": "null"}
    return _nullable(
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "gate_id": {"type": "string", "const": gate.id},
                "gate_revision": {"type": "string", "const": gate.revision},
                "prompt": {"type": "string"},
                "assistance": next_check_assistance_schema(),
            },
            "required": ["gate_id", "gate_revision", "prompt", "assistance"],
        }
    )


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    result = dict(schema)
    result["type"] = [str(schema["type"]), "null"]
    return result
