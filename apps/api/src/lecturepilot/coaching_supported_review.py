"""A successful supported retry schedules fresh delayed evidence after a real delay."""

from datetime import timedelta

from lecturepilot.coaching_state_models import review_key
from lecturepilot.coaching_task_bank import task_ids_for_stage


def schedule_after_supported_review(progress, *, gate, exposed_task_ids, now):
    task_id = next(
        (
            item
            for item in task_ids_for_stage(gate, "delayed_transfer")
            if item not in exposed_task_ids
        ),
        None,
    )
    current = progress.delayed_reviews.get(review_key(gate.id, gate.revision))
    if task_id is None or current is None:
        return
    progress.delayed_reviews[review_key(gate.id, gate.revision)] = current.model_copy(
        update={
            "task_id": task_id,
            "scheduled_at": now,
            "due_at": now + timedelta(seconds=current.planned_delay_seconds),
            "attempted_at": None,
            "observed_delay_seconds": None,
            "completed_at": None,
            "failed_since_review": True,
        }
    )
