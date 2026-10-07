"""Resolve an issued readiness task. Client policy text is never accepted."""

from fastapi import HTTPException

from lecturepilot.agent_context_models import AgentReadinessTask
from lecturepilot.readiness_progress import InvalidReadinessProgressError, ReadinessProgressStore
from lecturepilot.scaffold_policy import scaffold_policy_for_revision_task
from lecturepilot.storage_layout import StorageLayout


def issued_readiness_task(
    layout: StorageLayout,
    *,
    user_id: str,
    course_id: str,
    lecture_id: str,
    task_id: str,
) -> AgentReadinessTask:
    store = ReadinessProgressStore(layout)
    try:
        progress = store.read(user_id=user_id, course_id=course_id)
    except InvalidReadinessProgressError as exc:
        raise HTTPException(status_code=409, detail="Saved readiness progress is invalid.") from exc
    task = next(
        (
            item
            for item in progress.active_tasks
            if item.id == task_id and item.lecture_id == lecture_id and item.status == "open"
        ),
        None,
    )
    if task is None:
        raise HTTPException(
            status_code=404, detail="Readiness task was not issued to this learner."
        )
    return AgentReadinessTask(
        id=task.id,
        source_ref=task.source_ref,
        expected_evidence=task.expected_evidence,
        scaffold_policy=scaffold_policy_for_revision_task(
            guidance_level=task.guidance_level,
            task_kind=task.kind,
        ),
    )
