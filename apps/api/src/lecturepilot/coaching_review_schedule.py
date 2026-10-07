"""Deterministic spacing uses fresh reviewed tasks and never recycles exposure."""

from datetime import timedelta

from lecturepilot.coaching_task_bank import task_ids_for_stage, task_prompt

MAX_REVIEW_INTERVAL_DAYS = 60


def advance_review(current, *, gate, exposed_task_ids, now):
    fresh = next(
        (
            task_id
            for task_id in task_ids_for_stage(gate, "delayed_transfer")
            if task_id not in exposed_task_ids
        ),
        None,
    )
    if fresh is None:
        return current.model_copy(update={"completed_at": now, "last_completed_at": now})
    previous_days = max(1, current.planned_delay_seconds // (24 * 60 * 60))
    days = (
        gate.review_after_days
        if current.failed_since_review
        else min(max(MAX_REVIEW_INTERVAL_DAYS, gate.review_after_days), previous_days * 2)
    )
    seconds = days * 24 * 60 * 60
    return current.model_copy(
        update={
            "transfer_prompt": task_prompt(gate, fresh),
            "task_id": fresh,
            "scheduled_at": now,
            "due_at": now + timedelta(seconds=seconds),
            "planned_delay_seconds": seconds,
            "attempted_at": None,
            "completed_at": None,
            "observed_delay_seconds": None,
            "last_completed_at": now,
            "failed_since_review": False,
        }
    )
