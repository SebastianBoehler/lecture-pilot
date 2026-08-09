import json
from datetime import UTC, datetime, timedelta

from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.models import AgentCoachingContext, QualityGateDecision, QualityGateStatus
from lecturepilot.scaffold_policy import scaffold_policy_for_tutor_turn
from lecturepilot.storage_layout import StorageLayout

IDS = {"user_id": "student-1", "course_id": "course-1", "lecture_id": "lecture-1"}


def test_unsolicited_message_is_not_an_independent_attempt(tmp_path) -> None:
    store = CoachingProgressStore(StorageLayout(tmp_path))
    context = _context(store)

    event = store.record_turn(
        **IDS,
        context=context,
        policy=_policy(context),
        decision=_decision(QualityGateStatus.NEEDS_EVIDENCE),
    )

    assert (event.attempt_kind, event.attempt_index, event.independent_attempt) == (
        "none",
        None,
        False,
    )
    assert event.assistance_level == "none"


def test_bound_check_classifies_independent_then_supported_retry(tmp_path) -> None:
    store = CoachingProgressStore(StorageLayout(tmp_path))
    initial = _context(store)
    store.record_turn(
        **IDS,
        context=initial,
        policy=_policy(initial).model_copy(update={"assistance_level": "none"}),
        decision=_decision(
            QualityGateStatus.NOT_ASSESSED,
            next_prompt="Explain the held-out evaluation step.",
        ),
        gate_revision="revision-1",
    )

    first_context = _context(store)
    first_event = store.record_turn(
        **IDS,
        context=first_context,
        policy=_policy(first_context).model_copy(update={"assistance_level": "cue"}),
        decision=_decision(
            QualityGateStatus.NEEDS_EVIDENCE,
            next_prompt="Name the split that prevents leakage.",
            evidence_ids=["model-link"],
            missing_evidence_ids=["held-out-evaluation"],
        ),
        gate_revision="revision-1",
    )
    retry_context = _context(CoachingProgressStore(store.layout))
    retry_event = store.record_turn(
        **IDS,
        context=retry_context,
        policy=_policy(retry_context),
        decision=_decision(QualityGateStatus.PASSED),
        gate_revision="revision-1",
    )

    assert first_event.attempt_kind == "independent"
    assert first_event.attempt_index == 1
    assert first_event.assistance_level == "none"
    assert (retry_event.attempt_kind, retry_event.attempt_index) == ("supported_retry", 2)
    assert retry_event.assistance_level == "cue"
    assert retry_context.evidence_ids == ["model-link"]
    assert retry_context.missing_evidence_ids == ["held-out-evaluation"]


def test_learner_corrected_session_goal_is_used_on_the_next_turn(tmp_path) -> None:
    store = CoachingProgressStore(StorageLayout(tmp_path))
    context = _context(store)
    store.record_turn(
        **IDS,
        context=context,
        policy=_policy(context),
        decision=_decision(QualityGateStatus.NOT_ASSESSED),
        session_goal="Compare two validation strategies for my assignment.",
    )

    next_context = _context(store)

    assert next_context.session_goal == "Compare two validation strategies for my assignment."
    assert next_context.goal_is_new is False


def test_recent_conversation_is_bounded_to_eight_chronological_messages(tmp_path) -> None:
    store = CoachingProgressStore(StorageLayout(tmp_path))
    for index in range(5):
        store.record_exchange(
            **IDS,
            user_message=f"learner-{index}",
            assistant_message=f"tutor-{index}",
        )

    progress = store.read(**IDS)

    assert [(message.role, message.content) for message in progress.messages] == [
        ("user", "learner-1"),
        ("assistant", "tutor-1"),
        ("user", "learner-2"),
        ("assistant", "tutor-2"),
        ("user", "learner-3"),
        ("assistant", "tutor-3"),
        ("user", "learner-4"),
        ("assistant", "tutor-4"),
    ]


def test_read_migrates_legacy_delayed_transfer_without_erasing_progress(tmp_path) -> None:
    layout = StorageLayout(tmp_path)
    store = CoachingProgressStore(layout)
    path = layout.user_lecture_root(*IDS.values()) / "tutor-state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_legacy_payload()), encoding="utf-8")

    progress = store.read(**IDS)

    assert progress.session_goal == "Keep this goal."
    assert len(progress.turns) == 1
    assert set(progress.delayed_reviews) == {"gate-1", "gate-2"}
    assert progress.delayed_reviews["gate-1"].due_at == "2026-07-15T09:00:00+00:00"
    store.record_exchange(**IDS, user_message="Continue.", assistant_message="Next check.")
    assert "delayed_transfer" not in json.loads(path.read_text(encoding="utf-8"))


def test_delayed_reviews_coexist_and_completing_one_preserves_the_other(tmp_path) -> None:
    now = datetime(2026, 7, 13, 9, 0, tzinfo=UTC)
    store = CoachingProgressStore(StorageLayout(tmp_path))
    _pass_gate(store, "gate-1", "revision-1", 2, now)
    _pass_gate(store, "gate-2", "revision-2", 4, now)

    due = _context(
        store,
        gate_id="gate-1",
        revision="revision-1",
        now=now + timedelta(days=3),
    )
    store.record_turn(
        **IDS,
        context=due,
        policy=_policy(due),
        decision=_decision(
            QualityGateStatus.NOT_ASSESSED,
            gate_id="gate-1",
            next_prompt="Apply gate 1 to a new case.",
        ),
        gate_revision="revision-1",
        now=now + timedelta(days=3),
    )
    delayed_context = _context(
        store,
        gate_id="gate-1",
        revision="revision-1",
        now=now + timedelta(days=3, minutes=5),
    )
    event = store.record_turn(
        **IDS,
        context=delayed_context,
        policy=_policy(delayed_context),
        decision=_decision(QualityGateStatus.PASSED, gate_id="gate-1"),
        gate_revision="revision-1",
        now=now + timedelta(days=3, minutes=5),
    )

    progress = store.read(**IDS)
    assert set(progress.delayed_reviews) == {"gate-1", "gate-2"}
    assert progress.delayed_reviews["gate-1"].completed_at is not None
    assert progress.delayed_reviews["gate-2"].completed_at is None
    assert (event.attempt_kind, event.attempt_index) == ("delayed_transfer", 2)
    assert event.delay_seconds == 259_500


def test_new_gate_revision_replaces_stale_delayed_review(tmp_path) -> None:
    first = datetime(2026, 7, 13, 9, 0, tzinfo=UTC)
    store = CoachingProgressStore(StorageLayout(tmp_path))
    _pass_gate(store, "gate-1", "revision-1", 2, first)

    revised = first + timedelta(days=1)
    _pass_gate(store, "gate-1", "revision-2", 4, revised)

    review = store.read(**IDS).delayed_reviews["gate-1"]
    assert review.gate_revision == "revision-2"
    assert review.scheduled_at == revised.isoformat()
    assert review.due_at == (revised + timedelta(days=4)).isoformat()


def _pass_gate(store, gate_id: str, revision: str, review_days: int, now: datetime) -> None:
    initial = _context(store, gate_id=gate_id, revision=revision, now=now)
    store.record_turn(
        **IDS,
        context=initial,
        policy=_policy(initial).model_copy(update={"assistance_level": "none"}),
        decision=_decision(
            QualityGateStatus.NOT_ASSESSED,
            gate_id=gate_id,
            next_prompt=f"Answer {gate_id}.",
        ),
        gate_revision=revision,
        now=now,
    )
    attempt = _context(store, gate_id=gate_id, revision=revision, now=now)
    store.record_turn(
        **IDS,
        context=attempt,
        policy=_policy(attempt),
        decision=_decision(QualityGateStatus.PASSED, gate_id=gate_id),
        gate_revision=revision,
        review_after_days=review_days,
        now=now,
    )


def _context(
    store,
    *,
    gate_id: str = "gate-1",
    revision: str = "revision-1",
    now: datetime | None = None,
):
    return store.context(
        **IDS,
        gate_id=gate_id,
        gate_title="Model selection",
        gate_revision=revision,
        now=now,
    )


def _policy(context: AgentCoachingContext):
    return scaffold_policy_for_tutor_turn(
        attendance="present",
        delayed_transfer_due=context.delayed_transfer_due,
        last_gate_status=context.last_gate_status,
        needs_evidence_count=context.needs_evidence_count,
        prior_assistance=context.prior_assistance,
    )


def _decision(status, *, gate_id="gate-1", next_prompt=None, **evidence):
    return QualityGateDecision(
        gate_id=gate_id,
        status=status,
        reason="test",
        next_prompt=next_prompt,
        **evidence,
    )


def _legacy_payload() -> dict:
    return {
        "session_goal": "Keep this goal.",
        "goal_proposed": True,
        "turns": [
            {
                "created_at": "2026-07-13T09:00:00+00:00",
                "gate_id": "gate-1",
                "gate_status": "needs_evidence",
                "support_profile": "self_explanation",
                "process_label": "self_explanation",
                "independent_attempt": True,
            }
        ],
        "delayed_transfer": {"gate_id": "gate-1", "due_at": "2026-07-15T09:00:00+00:00"},
        "delayed_reviews": {
            "gate-2": {
                "gate_id": "gate-2",
                "gate_revision": "revision-2",
                "scheduled_at": "2026-07-13T09:00:00+00:00",
                "due_at": "2026-07-16T09:00:00+00:00",
            }
        },
    }
