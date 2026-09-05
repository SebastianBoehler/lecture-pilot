from __future__ import annotations

from typing import Any

from lecturepilot.learning_map import LearningMapGate


def assessment_schema(gate: LearningMapGate | None, *, required: bool = False) -> dict[str, Any]:
    if gate is None:
        return {"type": "null"}
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "gate_id": {"type": "string", "const": gate.id},
            "gate_revision": {"type": "string", "const": gate.revision},
            "reason": {"type": "string", "minLength": 1, "maxLength": 500},
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
    return schema if required else _nullable(schema)


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    result = dict(schema)
    result["type"] = [str(schema["type"]), "null"]
    return result
