from __future__ import annotations

from lecturepilot.coaching_assistance import NextCheck
from lecturepilot.learning_map import LearningMapGate
from lecturepilot.quality_gate_models import QualityGateDecision

_MAX_REASON_LENGTH = 500
_LEARNER_TEXT = {
    "en": {
        "passed": "Well done: your answer shows everything this check asks for.",
        "missing": "Not quite yet. Your answer still needs to show: {criteria}",
        "support": "Hint:",
        "next": "Next check:",
    },
    "de": {
        "passed": "Gut gemacht: Deine Antwort zeigt alles, was diese Aufgabe verlangt.",
        "missing": "Noch nicht ganz. Deine Antwort muss noch zeigen: {criteria}",
        "support": "Hinweis:",
        "next": "Nächste Aufgabe:",
    },
}


def assessment_reason(gate: LearningMapGate, missing_evidence_ids: list[str]) -> str:
    """Audit reason stored with the gate decision (stable English, not shown to learners)."""
    if not missing_evidence_ids:
        return "Assessment passed against the approved required evidence."
    label = "criterion" if len(missing_evidence_ids) == 1 else "criteria"
    reason = (
        f"More evidence is needed for the approved {label}: {_criteria(gate, missing_evidence_ids)}"
    )
    if not reason.endswith((".", "!", "?")):
        reason += "."
    if len(reason) <= _MAX_REASON_LENGTH:
        return reason
    return reason[: _MAX_REASON_LENGTH - 3].rstrip() + "..."


def compose_assessment_message(
    decision: QualityGateDecision,
    next_check: NextCheck | None,
    *,
    gate: LearningMapGate | None,
    locale: str,
) -> str:
    """Learner-facing result in the learner's language, derived from the backend decision."""
    text = _LEARNER_TEXT.get(locale, _LEARNER_TEXT["en"])
    if gate is None:
        parts = [decision.reason]
    elif decision.missing_evidence_ids:
        parts = [text["missing"].format(criteria=_criteria(gate, decision.missing_evidence_ids))]
    else:
        parts = [text["passed"]]
    if next_check is not None:
        if next_check.assistance.content is not None:
            parts.append(f"{text['support']}\n{next_check.assistance.content}")
        parts.append(f"{text['next']}\n{next_check.prompt}")
    return "\n\n".join(parts)


def _criteria(gate: LearningMapGate, evidence_ids: list[str]) -> str:
    descriptions = {item.id: item.description for item in gate.evidence_criteria}
    return "; ".join(descriptions[item] for item in evidence_ids)
