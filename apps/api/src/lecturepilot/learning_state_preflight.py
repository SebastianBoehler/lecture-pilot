from __future__ import annotations

from lecturepilot.coaching_progress import InvalidCoachingStateError
from lecturepilot.coaching_state_models import (
    CoachingProgress,
    hint_exposure_key,
    review_key,
)
from lecturepilot.coaching_transitions import prompt_for_stage
from lecturepilot.learning_map import LearningMap, LearningMapGate


def validate_coaching_bindings(progress: CoachingProgress, learning_map: LearningMap) -> None:
    gates = {gate.id: gate for gate in learning_map.gates}
    if progress.pending_check is not None:
        gate = _require_gate_revision(
            gates,
            gate_id=progress.pending_check.gate_id,
            gate_revision=progress.pending_check.gate_revision,
        )
        _validate_pending(progress, gate)
    for exposure in progress.hint_exposures.values():
        gate = _require_gate_revision(
            gates,
            gate_id=exposure.gate_id,
            gate_revision=exposure.gate_revision,
        )
        approved = next(
            (hint for hint in gate.hint_ladder if hint.level == exposure.assistance_level),
            None,
        )
        if approved is None or approved.content != exposure.content:
            raise InvalidCoachingStateError("Persisted tutor state is invalid.")
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
        pending = progress.pending_check
        if (
            review.attempted_at is not None
            and review.completed_at is None
            and (
                pending is None
                or pending.gate_id != review.gate_id
                or pending.gate_revision != review.gate_revision
                or pending.stage not in {"delayed_support", "delayed_transfer"}
            )
        ):
            raise InvalidCoachingStateError("Persisted tutor state is invalid.")


def _validate_pending(progress: CoachingProgress, gate: LearningMapGate) -> None:
    pending = progress.pending_check
    if pending is None:
        return
    if pending.prompt != prompt_for_stage(gate, pending.stage):
        raise InvalidCoachingStateError("Persisted tutor state is invalid.")
    if pending.assistance_level != "none":
        approved = next(
            (hint for hint in gate.hint_ladder if hint.level == pending.assistance_level),
            None,
        )
        key = hint_exposure_key(gate.revision, pending.assistance_level)
        exposure = progress.hint_exposures.get(key)
        if (
            approved is None
            or approved.content != pending.assistance_content
            or exposure is None
            or exposure.content != approved.content
            or exposure.gate_id != gate.id
        ):
            raise InvalidCoachingStateError("Persisted tutor state is invalid.")
    if pending.stage in {"delayed_transfer", "delayed_support"}:
        review = progress.delayed_reviews.get(review_key(gate.id, gate.revision))
        if review is None or review.completed_at is not None:
            raise InvalidCoachingStateError("Persisted tutor state is invalid.")
        if pending.stage == "delayed_support" and review.attempted_at is None:
            raise InvalidCoachingStateError("Persisted tutor state is invalid.")


def _require_gate_revision(
    gates: dict[str, LearningMapGate], *, gate_id: str, gate_revision: str
) -> LearningMapGate:
    gate = gates.get(gate_id)
    if gate is None or gate.revision != gate_revision:
        raise InvalidCoachingStateError("Persisted tutor state is invalid.")
    return gate
