from __future__ import annotations

from typing import Any

from lecturepilot.learning_map import LearningMapGate
from lecturepilot.provider_turn_result import ProviderQualityGateDecision
from lecturepilot.provider_json_schema import provider_json_schema


def assessment_schema(gate: LearningMapGate | None, *, required: bool = False) -> dict[str, Any]:
    if gate is None:
        return {"type": "null"}
    schema = provider_json_schema(ProviderQualityGateDecision)
    schema["properties"]["gate_id"]["const"] = gate.id
    schema["properties"]["gate_revision"]["const"] = gate.revision
    evidence = schema["properties"]["evidence_ids"]
    evidence["items"]["enum"] = [item.id for item in gate.evidence_criteria]
    evidence["maxItems"] = len(gate.evidence_criteria)
    return schema if required else _nullable(schema)


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    result = dict(schema)
    result["type"] = [str(schema["type"]), "null"]
    return result
