import asyncio
from types import SimpleNamespace

import pytest
from pydantic_ai.models.function import FunctionModel

from lecturepilot.authoring_job import run_authoring_job
from lecturepilot.course_canvas_generation_cancel import cancel_canvas_generation
from lecturepilot.course_canvas_generation_jobs import CanvasGenerationStore
from lecturepilot.course_canvas_generation_ownership import CanvasGenerationOwnershipError
from lecturepilot.course_canvas_generation_service import run_idempotent_canvas_generation
from lecturepilot.storage_layout import StorageLayout
from test_authoring_job import authoring_job


async def test_cancelled_author_preserves_cancellation_after_authority_is_revoked(tmp_path):
    app = SimpleNamespace(state=SimpleNamespace())
    store = CanvasGenerationStore(StorageLayout(tmp_path), lease_seconds=45)
    args = dict(
        course_id="course-a",
        lecture_id="lecture-01",
        actor_user_id="prof01",
        request_key="authoring-cancel-0001",
    )
    job = authoring_job(tmp_path)
    entered = asyncio.Event()

    def authorize():
        current = store.read(**args)
        if current is not None and current.status == "failed":
            raise CanvasGenerationOwnershipError("Generation ownership was revoked.")

    async def respond(messages, info):
        entered.set()
        await asyncio.Event().wait()

    async def generate(_id, _attempt):
        return (await run_authoring_job(job, model=FunctionModel(respond))).document

    job.authorize = authorize
    task = asyncio.create_task(
        run_idempotent_canvas_generation(app=app, store=store, generate=generate, **args)
    )
    await asyncio.wait_for(entered.wait(), 2)
    result = await cancel_canvas_generation(app=app, store=store, **args)
    with pytest.raises(asyncio.CancelledError):
        await task
    assert result.error_code == store.read(**args).error_code == "cancelled"
    assert (tmp_path / "job/session.json").is_file()
