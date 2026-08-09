from __future__ import annotations

from typing import Any

from lecturepilot.coaching_assistance import next_check_assistance_schema


def assessment_schema() -> dict[str, Any]:
    return _nullable(
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "gate_id": {"type": "string"},
                "gate_revision": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                "status": {"type": "string", "enum": ["passed", "needs_evidence"]},
                "reason": {"type": "string"},
                "evidence_ids": {"type": "array", "items": {"type": "string"}},
                "missing_evidence_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "gate_id",
                "gate_revision",
                "status",
                "reason",
                "evidence_ids",
                "missing_evidence_ids",
            ],
        }
    )


def next_check_schema() -> dict[str, Any]:
    return _nullable(
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "gate_id": {"type": "string"},
                "gate_revision": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
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
