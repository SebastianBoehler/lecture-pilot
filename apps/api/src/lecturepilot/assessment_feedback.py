from __future__ import annotations

from lecturepilot.coaching_assistance import NextCheck
from lecturepilot.learning_map import LearningMapGate
from lecturepilot.quality_gate_models import QualityGateDecision

_MAX_REASON_LENGTH = 500


def assessment_reason(gate: LearningMapGate, missing_evidence_ids: list[str]) -> str:
    if not missing_evidence_ids:
        return "Assessment passed against the approved required evidence."
    criteria = {item.id: item.description for item in gate.evidence_criteria}
    descriptions = [criteria[item] for item in missing_evidence_ids]
    label = "criterion" if len(descriptions) == 1 else "criteria"
    reason = f"More evidence is needed for the approved {label}: {'; '.join(descriptions)}"
    if not reason.endswith((".", "!", "?")):
        reason += "."
    if len(reason) <= _MAX_REASON_LENGTH:
        return reason
    return reason[: _MAX_REASON_LENGTH - 3].rstrip() + "..."


def compose_assessment_message(
    decision: QualityGateDecision,
    next_check: NextCheck | None,
) -> str:
    parts = [decision.reason]
    if next_check is not None:
        if next_check.assistance.content is not None:
            parts.append(f"Approved support:\n{next_check.assistance.content}")
        parts.append(f"Next check:\n{next_check.prompt}")
    return "\n\n".join(parts)
