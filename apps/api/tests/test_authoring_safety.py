import asyncio

import pytest
from pydantic_ai.models.function import FunctionModel

from authoring_test_helpers import markdown
from lecturepilot.authoring_job import run_authoring_job
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_quality import CanvasQualityReviewer
from test_authoring_job import VALID, authoring_job


async def test_section_that_never_validates_stays_repairable(tmp_path):
    def respond(messages, info):
        return markdown('<!-- block id="formula" type="math" -->\n```math\n\\custom{x}\n```\n')

    with pytest.raises(CanvasGenerationRepairableError, match="/draft/topic.md"):
        await run_authoring_job(authoring_job(tmp_path), model=FunctionModel(respond))
    assert (tmp_path / "job/draft/topic.md").exists()


async def test_model_output_only_lands_in_its_assigned_draft(tmp_path):
    evidence_before = None

    def respond(messages, info):
        nonlocal evidence_before
        evidence_before = (tmp_path / "job/evidence/topic.md").read_text()
        return markdown(VALID)

    await run_authoring_job(authoring_job(tmp_path), model=FunctionModel(respond))
    assert (tmp_path / "job/evidence/topic.md").read_text() == evidence_before
    assert sorted(p.name for p in (tmp_path / "job/draft").iterdir()) == ["topic.md"]


async def test_cancelled_job_retains_draft_for_explicit_resume(tmp_path):
    reached_critic = asyncio.Event()

    class BlockingCritic:
        async def complete_review(self, **kwargs):
            reached_critic.set()
            await asyncio.Event().wait()

    job = authoring_job(tmp_path)
    job.reviewer = CanvasQualityReviewer(BlockingCritic())
    calls = 0

    def respond(messages, info):
        nonlocal calls
        calls += 1
        return markdown(VALID)

    task = asyncio.create_task(run_authoring_job(job, model=FunctionModel(respond)))
    await asyncio.wait_for(reached_critic.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    result = await run_authoring_job(authoring_job(tmp_path), model=FunctionModel(respond))
    assert calls == 1
    assert result.metrics.resumes == 1


async def test_duplicate_worker_cannot_enter_same_job(tmp_path):
    entered = asyncio.Event()

    async def waiting(messages, info):
        entered.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(
        run_authoring_job(authoring_job(tmp_path), model=FunctionModel(waiting))
    )
    await asyncio.wait_for(entered.wait(), 2)
    try:
        with pytest.raises(RuntimeError, match="already running"):
            await asyncio.wait_for(
                run_authoring_job(authoring_job(tmp_path), model=FunctionModel(waiting)), 1
            )
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
