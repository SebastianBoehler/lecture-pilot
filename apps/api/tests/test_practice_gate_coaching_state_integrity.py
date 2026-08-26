from datetime import UTC, datetime, timedelta

import pytest

from lecturepilot.coaching_progress import InvalidCoachingStateError
from lecturepilot.coaching_episode import record_review_attempt, schedule_delayed_review
from lecturepilot.coaching_state_models import (
    CoachingProgress,
    HintExposure,
    PendingCheck,
    hint_exposure_key,
)
from lecturepilot.learning_map import LearningMap, LearningMapNode
from lecturepilot.learning_state_preflight import validate_coaching_bindings
from practice_gate_coaching_test_helpers import practice_gate


@pytest.mark.parametrize(
    "mutation",
    ["substitute_prompt", "substitute_pending_hint", "substitute_exposure_hint"],
)
def test_preflight_rejects_substituted_persisted_check_contract(mutation: str) -> None:
    gate = practice_gate()
    progress = _supported_progress()
    key = hint_exposure_key(gate.revision, "prompt")
    if mutation == "substitute_prompt":
        progress.pending_check = progress.pending_check.model_copy(
            update={"prompt": gate.independent_exit_task}
        )
    elif mutation == "substitute_pending_hint":
        progress.pending_check = progress.pending_check.model_copy(
            update={"assistance_content": "Invented pending help."}
        )
    else:
        progress.hint_exposures[key] = progress.hint_exposures[key].model_copy(
            update={"content": "Invented exposure."}
        )

    with pytest.raises(InvalidCoachingStateError, match="tutor state"):
        validate_coaching_bindings(progress, _map())


def test_preflight_accepts_exact_revision_level_and_approved_hint_content() -> None:
    validate_coaching_bindings(_supported_progress(), _map())


def test_preflight_rejects_an_attempted_review_without_its_bound_retry() -> None:
    gate = practice_gate()
    progress = CoachingProgress.empty(course_id="course-1", lecture_id="lecture-1")
    now = datetime(2026, 8, 26, 9, tzinfo=UTC)
    schedule_delayed_review(
        progress,
        gate_id=gate.id,
        gate_revision=gate.revision,
        section_id=gate.section_id,
        transfer_prompt=gate.transfer_prompt,
        review_after_days=gate.review_after_days,
        now=now,
    )
    record_review_attempt(
        progress,
        gate_id=gate.id,
        gate_revision=gate.revision,
        now=now + timedelta(days=gate.review_after_days),
    )

    with pytest.raises(InvalidCoachingStateError, match="tutor state"):
        validate_coaching_bindings(progress, _map())


def _supported_progress() -> CoachingProgress:
    gate = practice_gate()
    now = datetime(2026, 8, 26, 9, tzinfo=UTC)
    progress = CoachingProgress.empty(course_id="course-1", lecture_id="lecture-1")
    progress.pending_check = PendingCheck(
        gate_id=gate.id,
        gate_revision=gate.revision,
        prompt=gate.prompt,
        assistance_level="prompt",
        assistance_content="Name the invariant first.",
        kind="standard",
        stage="diagnostic_support",
        issued_at=now,
    )
    key = hint_exposure_key(gate.revision, "prompt")
    progress.hint_exposures[key] = HintExposure(
        gate_id=gate.id,
        gate_revision=gate.revision,
        assistance_level="prompt",
        content="Name the invariant first.",
        exposed_at=now,
    )
    return progress


def _map() -> LearningMap:
    gate = practice_gate()
    return LearningMap.create(
        course_id="course-1",
        lecture_id="lecture-1",
        title="Lecture",
        objective="Apply the invariant independently.",
        nodes=[
            LearningMapNode(
                id="mechanism",
                title="Mechanism",
                lecture_id="lecture-1",
                section_id="mechanism",
                source_ref="lecture.md",
                prerequisites=[],
                gate_ids=[gate.id],
                quiz_ids=[],
            )
        ],
        gates=[gate],
    )
