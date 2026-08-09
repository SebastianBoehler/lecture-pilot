from __future__ import annotations

from lecturepilot.coaching_progress import InvalidCoachingStateError
from lecturepilot.coaching_state_models import CoachingProgress
from lecturepilot.learning_map import LearningMap, LearningMapGate


def validate_coaching_bindings(progress: CoachingProgress, learning_map: LearningMap) -> None:
    gates = {gate.id: gate for gate in learning_map.gates}
    if progress.pending_check is not None:
        _require_gate_revision(
            gates,
            gate_id=progress.pending_check.gate_id,
            gate_revision=progress.pending_check.gate_revision,
        )
    for review in progress.delayed_reviews.values():
        gate = _require_gate_revision(
            gates,
            gate_id=review.gate_id,
            gate_revision=review.gate_revision,
        )
        if (
            review.section_id != gate.section_id
            or review.transfer_prompt != gate.transfer_prompt
            or review.planned_delay_seconds != gate.review_after_days * 24 * 60 * 60
        ):
            raise InvalidCoachingStateError("Persisted tutor state is invalid.")


def _require_gate_revision(
    gates: dict[str, LearningMapGate], *, gate_id: str, gate_revision: str
) -> LearningMapGate:
    gate = gates.get(gate_id)
    if gate is None or gate.revision != gate_revision:
        raise InvalidCoachingStateError("Persisted tutor state is invalid.")
    return gate
