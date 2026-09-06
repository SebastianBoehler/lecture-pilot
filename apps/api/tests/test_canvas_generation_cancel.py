import asyncio
from types import SimpleNamespace

import pytest

from lecturepilot.course_canvas_generation_cancel import cancel_canvas_generation
from lecturepilot.course_canvas_generation_jobs import CanvasGenerationStore
from lecturepilot.course_canvas_generation_service import run_idempotent_canvas_generation
from lecturepilot.storage_layout import StorageLayout


async def test_explicit_cancel_stops_worker_and_persists_cancelled_status(tmp_path):
    app = SimpleNamespace(state=SimpleNamespace())
    store = CanvasGenerationStore(StorageLayout(tmp_path), lease_seconds=45)
    entered = asyncio.Event()
    args = dict(
        course_id="course-a",
        lecture_id="lecture-01",
        actor_user_id="prof01",
        request_key="cancel-request-0001",
    )

    async def generate(_id, _attempt):
        entered.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(
        run_idempotent_canvas_generation(app=app, store=store, generate=generate, **args)
    )
    await asyncio.wait_for(entered.wait(), 2)
    result = await cancel_canvas_generation(app=app, store=store, **args)
    with pytest.raises(asyncio.CancelledError):
        await task
    assert result.status == "failed"
    assert store.read(**args).error_code == "cancelled"
    assert (await cancel_canvas_generation(app=app, store=store, **args)).error_code == "cancelled"
