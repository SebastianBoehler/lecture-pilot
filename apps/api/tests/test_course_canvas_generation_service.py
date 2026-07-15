from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_generation_jobs import CanvasGenerationStore
from lecturepilot.course_canvas_generation_service import (
    CANVAS_GENERATION_LEASE_SECONDS,
    CanvasGenerationReplayError,
    run_idempotent_canvas_generation,
)
from lecturepilot.storage_layout import StorageLayout


@pytest.mark.asyncio
async def test_duplicate_request_waits_for_and_replays_one_generation(tmp_path) -> None:
    app = SimpleNamespace(state=SimpleNamespace())
    store = CanvasGenerationStore(
        StorageLayout(tmp_path), lease_seconds=CANVAS_GENERATION_LEASE_SECONDS
    )
    calls = 0
    release = asyncio.Event()

    async def generate(_generation_id: str, _attempt: int) -> CanvasDocument:
        nonlocal calls
        calls += 1
        await release.wait()
        return _canvas()

    first = asyncio.create_task(_run(app, store, generate))
    await asyncio.sleep(0)
    duplicate = asyncio.create_task(_run(app, store, generate))
    await asyncio.sleep(0.01)
    release.set()
    first_result, duplicate_result = await asyncio.gather(first, duplicate)

    assert calls == 1
    assert duplicate_result.job.generation_id == first_result.job.generation_id
    assert duplicate_result.canvas == first_result.canvas
    restarted_store = CanvasGenerationStore(
        StorageLayout(tmp_path), lease_seconds=CANVAS_GENERATION_LEASE_SECONDS
    )
    replayed = await _run(app, restarted_store, generate)
    assert replayed.job.generation_id == first_result.job.generation_id
    assert calls == 1


@pytest.mark.asyncio
async def test_generation_survives_disconnected_waiter_and_can_reconnect(tmp_path) -> None:
    app = SimpleNamespace(state=SimpleNamespace())
    store = CanvasGenerationStore(
        StorageLayout(tmp_path), lease_seconds=CANVAS_GENERATION_LEASE_SECONDS
    )
    release = asyncio.Event()
    calls = 0

    async def generate(_generation_id: str, _attempt: int) -> CanvasDocument:
        nonlocal calls
        calls += 1
        await release.wait()
        return _canvas()

    disconnected = asyncio.create_task(_run(app, store, generate))
    await asyncio.sleep(0)
    disconnected.cancel()
    with pytest.raises(asyncio.CancelledError):
        await disconnected
    release.set()
    await asyncio.sleep(0)

    reconnected = await _run(app, store, generate)

    assert calls == 1
    assert reconnected.canvas.title == "Persistent canvas"


@pytest.mark.asyncio
async def test_running_job_is_reclaimed_after_its_lease_expires(tmp_path) -> None:
    layout = StorageLayout(tmp_path)
    store = CanvasGenerationStore(layout, lease_seconds=0)
    original, owns_original = store.begin(
        course_id="course-1",
        lecture_id="lecture-01",
        actor_user_id="professor-1",
        request_key="request-key-0001",
    )

    restarted_app = SimpleNamespace(state=SimpleNamespace())
    result = await _run(restarted_app, store, lambda _id, _attempt: _return_canvas())

    assert owns_original is True
    assert result.job.generation_id == original.generation_id
    assert result.job.attempt == 2
    assert result.job.status == "completed"


@pytest.mark.asyncio
async def test_other_worker_waits_for_live_generation_instead_of_reclaiming(tmp_path) -> None:
    first_app = SimpleNamespace(state=SimpleNamespace())
    second_app = SimpleNamespace(state=SimpleNamespace())
    store = CanvasGenerationStore(
        StorageLayout(tmp_path), lease_seconds=CANVAS_GENERATION_LEASE_SECONDS
    )
    release = asyncio.Event()
    calls = 0

    async def generate(_generation_id: str, _attempt: int) -> CanvasDocument:
        nonlocal calls
        calls += 1
        await release.wait()
        return _canvas()

    first = asyncio.create_task(_run(first_app, store, generate))
    await asyncio.sleep(0)
    second = asyncio.create_task(_run(second_app, store, generate))
    await asyncio.sleep(0.01)

    assert calls == 1
    release.set()
    first_result, second_result = await asyncio.gather(first, second)
    assert first_result.job.generation_id == second_result.job.generation_id
    assert second_result.job.attempt == 1


@pytest.mark.asyncio
async def test_failed_generation_is_replayed_without_paid_retry(tmp_path) -> None:
    app = SimpleNamespace(state=SimpleNamespace())
    store = CanvasGenerationStore(
        StorageLayout(tmp_path), lease_seconds=CANVAS_GENERATION_LEASE_SECONDS
    )
    calls = 0

    async def generate(_generation_id: str, _attempt: int) -> CanvasDocument:
        nonlocal calls
        calls += 1
        raise RuntimeError("private provider detail")

    with pytest.raises(RuntimeError):
        await _run(app, store, generate)
    with pytest.raises(CanvasGenerationReplayError) as replay:
        await _run(app, store, generate)

    assert calls == 1
    assert replay.value.error_code == "runtime_error"


def _run(app, store, generate):
    return run_idempotent_canvas_generation(
        app=app,
        store=store,
        course_id="course-1",
        lecture_id="lecture-01",
        actor_user_id="professor-1",
        request_key="request-key-0001",
        generate=generate,
    )


def _canvas() -> CanvasDocument:
    return CanvasDocument(
        id="course-1-lecture-01",
        course_id="course-1",
        lecture_id="lecture-01",
        title="Persistent canvas",
        source_kind="generated",
        source_ref="Lecture01.tex",
        workspace_path="private/canvas/index.md",
        sections=[
            CanvasSection(
                id="summary",
                title="Summary",
                blocks=[CanvasBlock(id="summary-p", type="paragraph", text="Evidence")],
            )
        ],
    )


async def _return_canvas() -> CanvasDocument:
    return _canvas()
