"""Background learning-goal proposals for lectures added by a course update.

The proposal parses sources and makes model calls, so an update's HTTP request only records
a durable ``running`` marker per new lecture and schedules one asyncio task. The task
proposes goals lecture by lecture through the same workflow as the proposal endpoint and
renews the markers while it waits or works; a marker whose lease expired (for example after
a restart) no longer reports ``proposing``. Failures are recorded for the state endpoint;
the professor can always propose again from the goal review.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, ValidationError

from lecturepilot.core.durable_files import atomic_write_text
from lecturepilot.core.storage_layout import StorageLayout, safe_id
from lecturepilot.learning_design.course_practice_design_route_context import (
    _source_context,
    _source_revision,
)
from lecturepilot.learning_design.learning_goal_proposal_run import propose_lecture_goals
from lecturepilot.llm.generation_slots import background_generation_slot

GOAL_PROPOSAL_LEASE = timedelta(seconds=60)
GOAL_PROPOSAL_HEARTBEAT_SECONDS = 15


class GoalProposalJob(BaseModel):
    course_id: str = Field(min_length=1, max_length=120)
    lecture_id: str = Field(min_length=1, max_length=120)
    status: Literal["running", "completed", "failed"]
    started_at: datetime
    updated_at: datetime
    error_detail: str | None = Field(default=None, max_length=1_000)

    def proposing(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        return self.status == "running" and current - self.updated_at <= GOAL_PROPOSAL_LEASE


def goal_proposal_path(layout: StorageLayout, course_id: str, lecture_id: str) -> Path:
    return (
        layout.course_root(course_id) / "builder" / "goal-proposals" / f"{safe_id(lecture_id)}.json"
    )


def read_goal_proposal(
    layout: StorageLayout, course_id: str, lecture_id: str
) -> GoalProposalJob | None:
    path = goal_proposal_path(layout, course_id, lecture_id)
    if not path.exists():
        return None
    try:
        return GoalProposalJob.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return None


def mark_goal_proposals_running(
    layout: StorageLayout, course_id: str, lecture_ids: list[str]
) -> None:
    now = datetime.now(UTC)
    for lecture_id in lecture_ids:
        _write(
            layout,
            GoalProposalJob(
                course_id=course_id,
                lecture_id=lecture_id,
                status="running",
                started_at=now,
                updated_at=now,
            ),
        )


def start_goal_proposals(
    app: Any,
    *,
    course_id: str,
    lecture_ids: list[str],
    actor_user_id: str,
    source_document: Callable,
) -> asyncio.Task:
    """Schedule proposals on the running event loop; call after marking them running."""
    task = asyncio.create_task(
        _propose_all(app, course_id, list(lecture_ids), actor_user_id, source_document)
    )
    tasks = getattr(app.state, "goal_proposal_tasks", None)
    if tasks is None:
        tasks = app.state.goal_proposal_tasks = set()
    tasks.add(task)  # Keep a reference until the task finishes.
    task.add_done_callback(tasks.discard)
    return task


async def _propose_all(app, course_id, lecture_ids, actor_user_id, source_document) -> None:
    layout = app.state.canvas_workspace.layout
    pending = list(lecture_ids)
    heartbeat = asyncio.create_task(_heartbeat(layout, course_id, pending))
    try:
        for lecture_id in list(lecture_ids):
            status, detail = "completed", None
            try:
                async with background_generation_slot(app):
                    await propose_lecture_goals(
                        app,
                        course_id=course_id,
                        lecture_id=lecture_id,
                        actor_user_id=actor_user_id,
                        refresh=False,
                        source_document=source_document,
                        source_context=_source_context,
                        source_revision=_source_revision,
                    )
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - every failure is recorded for review.
                status, detail = "failed", str(getattr(exc, "detail", None) or exc)[:1_000]
            pending.remove(lecture_id)
            await run_in_threadpool(_finish, layout, course_id, lecture_id, status, detail)
    finally:
        heartbeat.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat


async def _heartbeat(layout, course_id: str, pending: list[str]) -> None:
    while True:
        await asyncio.sleep(GOAL_PROPOSAL_HEARTBEAT_SECONDS)
        await run_in_threadpool(_touch, layout, course_id, list(pending))


def _touch(layout, course_id: str, lecture_ids: list[str]) -> None:
    now = datetime.now(UTC)
    for lecture_id in lecture_ids:
        job = read_goal_proposal(layout, course_id, lecture_id)
        if job is not None and job.status == "running":
            _write(layout, job.model_copy(update={"updated_at": now}))


def _finish(layout, course_id, lecture_id, status, detail) -> None:
    job = read_goal_proposal(layout, course_id, lecture_id)
    now = datetime.now(UTC)
    _write(
        layout,
        GoalProposalJob(
            course_id=course_id,
            lecture_id=lecture_id,
            status=status,
            started_at=job.started_at if job else now,
            updated_at=now,
            error_detail=detail,
        ),
    )


def _write(layout: StorageLayout, job: GoalProposalJob) -> None:
    path = goal_proposal_path(layout, job.course_id, job.lecture_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, job.model_dump_json(indent=2))
