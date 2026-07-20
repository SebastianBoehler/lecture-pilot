from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
import re
from typing import Any

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_generation_jobs import (
    CanvasGenerationJob,
    CanvasGenerationStore,
    CanvasGenerationStoreError,
)
from lecturepilot.course_canvas_repair_target import CanvasGenerationRepairTarget


CANVAS_GENERATION_TIMEOUT_SECONDS = 900
CANVAS_GENERATION_LEASE_SECONDS = 45
CANVAS_GENERATION_HEARTBEAT_SECONDS = 10
_REQUEST_KEY = re.compile(r"^[A-Za-z0-9._:-]{16,128}$")


class CanvasGenerationReplayError(RuntimeError):
    def __init__(self, error_code: str | None) -> None:
        super().__init__("Previous canvas generation attempt failed.")
        self.error_code = error_code or "generation_failed"


class CanvasGenerationInProgressError(RuntimeError):
    pass


class CanvasGenerationTimeoutError(RuntimeError):
    pass


@dataclass(frozen=True)
class CanvasGenerationOutcome:
    job: CanvasGenerationJob
    canvas: CanvasDocument


def validate_generation_request_key(value: str) -> str:
    if not _REQUEST_KEY.fullmatch(value):
        raise ValueError("Idempotency-Key must be 16-128 URL-safe characters.")
    return value


async def run_idempotent_canvas_generation(
    *,
    app: Any,
    store: CanvasGenerationStore,
    course_id: str,
    lecture_id: str,
    actor_user_id: str,
    request_key: str,
    generate: Callable[[str, int], Awaitable[CanvasDocument]],
) -> CanvasGenerationOutcome:
    job, owns_attempt = store.begin(
        course_id=course_id,
        lecture_id=lecture_id,
        actor_user_id=actor_user_id,
        request_key=request_key,
    )
    if job.status == "completed" and job.canvas is not None:
        return CanvasGenerationOutcome(job, job.canvas)
    if job.status == "failed":
        raise CanvasGenerationReplayError(job.error_code)
    if not owns_attempt:
        active = _background_tasks(app).get(job.generation_id)
        if active is not None and not active.done():
            return await asyncio.shield(active)
        job, owns_attempt = await _wait_for_existing_or_claim(
            store,
            course_id=course_id,
            lecture_id=lecture_id,
            actor_user_id=actor_user_id,
            request_key=request_key,
        )
        if not owns_attempt:
            return CanvasGenerationOutcome(job, _completed_canvas(job))

    task = asyncio.create_task(
        _execute(
            store,
            job,
            actor_user_id=actor_user_id,
            request_key=request_key,
            generate=generate,
        )
    )
    tasks = _background_tasks(app)
    tasks[job.generation_id] = task
    task.add_done_callback(
        lambda completed: _finish_background(tasks, job.generation_id, completed)
    )
    return await asyncio.shield(task)


async def _execute(
    store: CanvasGenerationStore,
    job: CanvasGenerationJob,
    *,
    actor_user_id: str,
    request_key: str,
    generate: Callable[[str, int], Awaitable[CanvasDocument]],
) -> CanvasGenerationOutcome:
    heartbeat = asyncio.create_task(
        _heartbeat(
            store,
            job,
            actor_user_id=actor_user_id,
            request_key=request_key,
        )
    )
    try:
        async with asyncio.timeout(CANVAS_GENERATION_TIMEOUT_SECONDS):
            canvas = await generate(job.generation_id, job.attempt)
    except asyncio.CancelledError:
        store.fail(
            job,
            actor_user_id=actor_user_id,
            request_key=request_key,
            error_code="interrupted",
        )
        raise
    except TimeoutError as exc:
        store.fail(
            job,
            actor_user_id=actor_user_id,
            request_key=request_key,
            error_code="timeout",
        )
        raise CanvasGenerationTimeoutError("Canvas generation timed out.") from exc
    except Exception as exc:
        repair = _repair_metadata(exc)
        store.fail(
            job,
            actor_user_id=actor_user_id,
            request_key=request_key,
            error_code=_error_code(exc),
            error_detail=_error_detail(exc),
            **repair,
        )
        raise
    finally:
        heartbeat.cancel()
        with suppress(asyncio.CancelledError, OSError, CanvasGenerationStoreError):
            await heartbeat
    completed = store.complete(
        job,
        canvas,
        actor_user_id=actor_user_id,
        request_key=request_key,
    )
    return CanvasGenerationOutcome(completed, canvas)


async def _heartbeat(
    store: CanvasGenerationStore,
    job: CanvasGenerationJob,
    *,
    actor_user_id: str,
    request_key: str,
) -> None:
    while True:
        await asyncio.sleep(CANVAS_GENERATION_HEARTBEAT_SECONDS)
        store.touch(
            job,
            actor_user_id=actor_user_id,
            request_key=request_key,
        )


async def _wait_for_existing_or_claim(
    store: CanvasGenerationStore,
    *,
    course_id: str,
    lecture_id: str,
    actor_user_id: str,
    request_key: str,
) -> tuple[CanvasGenerationJob, bool]:
    deadline = asyncio.get_running_loop().time() + CANVAS_GENERATION_TIMEOUT_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(0.25)
        job, owns_attempt = store.begin(
            course_id=course_id,
            lecture_id=lecture_id,
            actor_user_id=actor_user_id,
            request_key=request_key,
        )
        if owns_attempt:
            return job, True
        if job.status == "completed":
            return job, False
        if job.status == "failed":
            raise CanvasGenerationReplayError(job.error_code)
    raise CanvasGenerationInProgressError("Canvas generation is still running.")


def _completed_canvas(job: CanvasGenerationJob) -> CanvasDocument:
    if job.status != "completed" or job.canvas is None:
        raise CanvasGenerationReplayError(job.error_code)
    return job.canvas


def _background_tasks(app: Any) -> dict[str, asyncio.Task[CanvasGenerationOutcome]]:
    tasks = getattr(app.state, "canvas_generation_tasks", None)
    if tasks is None:
        tasks = {}
        app.state.canvas_generation_tasks = tasks
    return tasks


def _finish_background(
    tasks: dict[str, asyncio.Task[CanvasGenerationOutcome]],
    generation_id: str,
    task: asyncio.Task[CanvasGenerationOutcome],
) -> None:
    if tasks.get(generation_id) is task:
        tasks.pop(generation_id, None)
    if not task.cancelled():
        task.exception()


def _error_code(exc: Exception) -> str:
    name = type(exc).__name__
    safe = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    return safe[:80] or "generation_failed"


def _error_detail(exc: Exception) -> str:
    return str(exc).strip()[:1_000] or "Canvas generation failed."


def _repair_metadata(exc: Exception) -> dict:
    if not isinstance(exc, CanvasGenerationRepairableError):
        return {}
    return {
        "repair": (
            CanvasGenerationRepairTarget(
                candidate=exc.candidate,
                section_id=exc.section_id,
                block_id=exc.block_id,
                source_revision=exc.source_revision,
            )
            if exc.candidate is not None and exc.section_id is not None
            else None
        )
    }
