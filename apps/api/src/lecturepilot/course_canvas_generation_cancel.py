import asyncio
from contextlib import suppress

from lecturepilot.course_canvas_generation_jobs import CanvasGenerationStoreError
from lecturepilot.course_canvas_generation_ownership import revoke_generation_ownership
from lecturepilot.course_update_recovery import locked_course_state


async def cancel_canvas_generation(
    *, app, store, course_id, lecture_id, actor_user_id, request_key
):
    args = dict(
        course_id=course_id,
        lecture_id=lecture_id,
        actor_user_id=actor_user_id,
        request_key=request_key,
    )
    with locked_course_state(store.layout.course_root(course_id)):
        job = store.read(**args)
        if job is None or job.status != "running":
            return job
        try:
            result = store.fail(
                job,
                actor_user_id=actor_user_id,
                request_key=request_key,
                error_code="cancelled",
                error_detail="Generation was cancelled by its owner.",
            )
        except CanvasGenerationStoreError:
            return store.read(**args)
        revoke_generation_ownership(store.layout, job)
    task = getattr(app.state, "canvas_generation_tasks", {}).get(job.generation_id)
    if task is not None and not task.done():
        task.cancel()
        with suppress(asyncio.CancelledError, CanvasGenerationStoreError):
            await task
    return result
