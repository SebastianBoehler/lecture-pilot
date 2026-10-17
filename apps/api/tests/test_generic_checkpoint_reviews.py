from datetime import timedelta

from auth_helpers import student_headers
from lecturepilot.learner.coaching_progress import CoachingProgressStore
from lecturepilot.learner.coaching_state_models import DelayedReview, review_key
from lecturepilot.learner.review_queue import ReviewQueueLecture, ReviewQueueStore
from test_review_checkpoint_routes import setup


def test_reviewed_target_issues_its_concrete_changed_task_after_independent_success(tmp_path):
    from lecturepilot.core.storage_layout import StorageLayout
    from lecturepilot.learner.coaching_check_binding import bind_delayed_review
    from lecturepilot.learner.quality_gate_models import QualityGateStatus
    from practice_gate_coaching_test_helpers import IDS, NOW, check, practice_gate
    from test_practice_gate_coaching_transitions import _record

    changed_task = (
        "A tank receives 8 litres per minute and loses 3 litres per minute. "
        "Calculate the volume change after 4 minutes and explain your reasoning."
    )
    gate = practice_gate(
        baseline_task="A tank receives 6 litres per minute. Calculate the inflow after 2 minutes.",
        independent_exit_task="A tank receives 5 litres per minute. Calculate the inflow after 3 minutes.",
        delayed_transfer_task=changed_task,
    )
    store = CoachingProgressStore(StorageLayout(tmp_path))
    store.bind_inline_checkpoint(**IDS, gate=gate, now=NOW)
    _record(
        store,
        gate,
        status=QualityGateStatus.PASSED,
        next_check=check(gate, gate.independent_exit_task, "none", None),
        now=NOW,
    )
    _record(store, gate, status=QualityGateStatus.PASSED, next_check=None, now=NOW)
    [review] = store.read(**IDS).delayed_reviews.values()

    pending = bind_delayed_review(
        store, **IDS, gate_id=gate.id, gate_revision=gate.revision, now=review.due_at
    )

    assert pending.prompt == changed_task
    assert pending.task_id == "delayed-transfer"
    assert pending.stage == "delayed_transfer"
    assert pending.assistance_level == "none"


def test_generic_checkpoint_has_no_generated_delayed_task(tmp_path):
    _, gate, _, _ = setup(tmp_path)

    assert gate.transfer_prompt is None


def save_legacy_review(client, gate, ids):
    from datetime import UTC, datetime

    store = CoachingProgressStore(client.app.state.canvas_workspace.layout)
    progress = store.read(**ids)
    now = datetime.now(UTC)
    progress.delayed_reviews[review_key(gate.id, gate.revision)] = DelayedReview(
        gate_id=gate.id,
        gate_revision=gate.revision,
        section_id=gate.section_id,
        transfer_prompt="Apply the same reasoning to a changed case: Explain the cause and its effect.",
        scheduled_at=now - timedelta(days=3),
        due_at=now - timedelta(days=1),
        planned_delay_seconds=172800,
        attempted_at=None,
        completed_at=None,
        observed_delay_seconds=None,
    )
    store._write(**ids, progress=progress)


def test_queue_does_not_offer_legacy_generic_delayed_reviews(tmp_path):
    client, gate, ids, _ = setup(tmp_path)
    save_legacy_review(client, gate, ids)
    learning_map = client.app.state.canvas_workspace.course_canvas_store.learning_map(
        course_id=ids["course_id"], lecture_id=ids["lecture_id"]
    )

    queue = ReviewQueueStore(client.app.state.canvas_workspace.layout).read_course(
        user_id=ids["user_id"],
        course_id=ids["course_id"],
        lectures=[
            ReviewQueueLecture(id=ids["lecture_id"], title="Lecture", learning_map=learning_map)
        ],
    )

    assert queue.items == []
    assert queue.upcoming == []
    assert queue.completed == []


def test_open_rejects_legacy_generic_delayed_review(tmp_path):
    client, gate, ids, _ = setup(tmp_path)
    save_legacy_review(client, gate, ids)

    result = client.post(
        f"/courses/{ids['course_id']}/review-queue/gates/{ids['lecture_id']}/{gate.id}/open",
        headers=student_headers(ids["user_id"]),
    )

    assert result.status_code == 409
    assert "reviewed practice target" in result.json()["detail"]
