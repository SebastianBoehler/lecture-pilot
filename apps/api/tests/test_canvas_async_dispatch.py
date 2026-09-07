import asyncio
from types import SimpleNamespace

import pytest

from lecturepilot.course_canvas_async_response import accepted_generation_response
from lecturepilot.course_canvas_generation_jobs import CanvasGenerationJob, CanvasGenerationStore
from lecturepilot.course_canvas_generation_service import run_idempotent_canvas_generation
from lecturepilot.storage_layout import StorageLayout
from test_course_canvas_generation_service import _canvas


@pytest.mark.asyncio
async def test_dispatch_releases_connections_before_generation_and_deduplicates(tmp_path):
    app = SimpleNamespace(state=SimpleNamespace())
    store = CanvasGenerationStore(StorageLayout(tmp_path), lease_seconds=45)
    release = asyncio.Event()
    started = []

    async def generate(generation_id, attempt):
        started.append(generation_id)
        await release.wait()
        return _canvas()

    async def dispatch(index, wait=False):
        return await run_idempotent_canvas_generation(
            app=app,
            store=store,
            course_id="course-1",
            lecture_id=f"lecture-{index:02}",
            actor_user_id="professor-1",
            request_key=f"request-key-{index:04}",
            generate=generate,
            wait_for_completion=wait,
        )

    jobs = await asyncio.wait_for(asyncio.gather(*(dispatch(i) for i in range(1, 15))), 2)
    await asyncio.sleep(0)
    assert len(started) == 14
    assert all(isinstance(job, CanvasGenerationJob) for job in jobs)
    assert (await dispatch(1)).generation_id == jobs[0].generation_id
    response = accepted_generation_response(jobs[0])
    assert response.status_code == 202
    assert response.headers["Preference-Applied"] == "respond-async"
    release.set()
    results = await asyncio.gather(*(dispatch(i, True) for i in range(1, 15)))
    assert len(started) == 14
    assert all(result.job.status == "completed" for result in results)
