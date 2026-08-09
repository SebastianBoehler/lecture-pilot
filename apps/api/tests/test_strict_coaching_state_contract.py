import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lecturepilot.coaching_episode import parse_time, record_passed_review
from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.coaching_state_models import CoachingProgress, CoachingTurnEvent, DelayedReview
from lecturepilot.storage_layout import StorageLayout

IDS = {"user_id": "student-1", "course_id": "course-1", "lecture_id": "lecture-1"}


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        json.dumps({"session_goal": "legacy incomplete state"}).encode(),
        json.dumps(
            {
                "session_goal": "",
                "goal_proposed": False,
                "turns": [],
                "delayed_transfer": {"gate_id": "gate-1"},
            }
        ).encode(),
    ],
)
def test_coaching_store_rejects_corrupt_or_obsolete_state_without_rewriting(
    tmp_path, payload: bytes
) -> None:
    store = CoachingProgressStore(StorageLayout(tmp_path))
    path = store.layout.user_lecture_root(*IDS.values()) / "tutor-state.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(payload)

    with pytest.raises(ValueError, match="tutor state"):
        store.read(**IDS)

    assert path.read_bytes() == payload


def test_coaching_event_rejects_revisionless_or_redundant_attempt_fields() -> None:
    valid = {
        "created_at": "2026-08-09T08:00:00+00:00",
        "gate_id": "gate-1",
        "gate_revision": "a" * 64,
        "gate_status": "needs_evidence",
        "support_profile": "self_explanation",
        "process_label": "self_explanation",
        "attempt_kind": "independent",
        "attempt_index": 1,
        "assistance_level": "none",
        "planned_delay_seconds": None,
        "observed_delay_seconds": None,
        "evidence_ids": [],
        "missing_evidence_ids": ["mechanism"],
    }
    with pytest.raises(ValidationError):
        CoachingTurnEvent.model_validate(
            {key: value for key, value in valid.items() if key != "gate_revision"}
        )
    with pytest.raises(ValidationError):
        CoachingTurnEvent.model_validate({**valid, "independent_attempt": True})


def test_delayed_review_requires_exact_contract_and_aware_times() -> None:
    with pytest.raises(ValidationError):
        DelayedReview.model_validate(
            {
                "gate_id": "gate-1",
                "gate_revision": "a" * 64,
                "due_at": "2026-08-11T08:00:00+00:00",
            }
        )
    with pytest.raises(ValueError, match="timezone"):
        parse_time("2026-08-11T08:00:00")


def test_delayed_reviews_keep_each_revision_and_stored_delay(tmp_path) -> None:
    progress = CoachingProgress.empty(course_id="course-1", lecture_id="lecture-1")
    now = datetime(2026, 8, 9, 8, 0, tzinfo=UTC)
    first_revision = "a" * 64
    second_revision = "b" * 64

    record_passed_review(
        progress,
        gate_id="gate-1",
        gate_revision=first_revision,
        section_id="section-1",
        transfer_prompt="Apply gate 1 to changed case A.",
        delayed_attempt=False,
        review_after_days=2,
        now=now,
    )
    record_passed_review(
        progress,
        gate_id="gate-1",
        gate_revision=second_revision,
        section_id="section-1-revised",
        transfer_prompt="Apply gate 1 to changed case B.",
        delayed_attempt=False,
        review_after_days=4,
        now=now + timedelta(days=1),
    )

    assert set(progress.delayed_reviews) == {
        f"gate-1@{first_revision}",
        f"gate-1@{second_revision}",
    }
    assert progress.delayed_reviews[f"gate-1@{first_revision}"].planned_delay_seconds == 172800
    assert progress.delayed_reviews[f"gate-1@{second_revision}"].planned_delay_seconds == 345600
    assert progress.delayed_reviews[f"gate-1@{second_revision}"].section_id == "section-1-revised"
