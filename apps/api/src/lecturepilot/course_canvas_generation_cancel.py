import asyncio
from contextlib import suppress

from fastapi.concurrency import run_in_threadpool

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

    def cancel_locked():
        with locked_course_state(store.layout.course_root(course_id)):
            job = store.read(**args)
            if job is None or job.status != "running":
                return job, job, False
            try:
                result = store.fail(
                    job,
                    actor_user_id=actor_user_id,
                    request_key=request_key,
                    error_code="cancelled",
                    error_detail="Generation was cancelled by its owner.",
                )
            except CanvasGenerationStoreError:
                return job, store.read(**args), False
            revoke_generation_ownership(store.layout, job)
            return job, result, True

    job, result, cancelled = await run_in_threadpool(cancel_locked)
    if not cancelled:
        return result
    task = getattr(app.state, "canvas_generation_tasks", {}).get(job.generation_id)
    if task is not None and not task.done():
        task.cancel()
        with suppress(asyncio.CancelledError, CanvasGenerationStoreError):
            await task
    return result
