import asyncio

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.authoring_job import run_authoring_job
from lecturepilot.authoring_models import AuthoringStalledError
from test_authoring_job import authoring_job


async def test_agent_cannot_complete_without_valid_draft(tmp_path):
    def respond(messages, info):
        return ModelResponse(parts=[ToolCallPart("final_result", {"ready": True})])

    with pytest.raises(AuthoringStalledError, match="same invalid draft"):
        await run_authoring_job(authoring_job(tmp_path), model=FunctionModel(respond))


@pytest.mark.parametrize("path", ["/evidence/topic.md", "/draft/other.md", "/users/memory.md"])
async def test_agent_cannot_write_outside_assigned_draft(tmp_path, path):
    calls = 0

    def respond(messages, info):
        nonlocal calls
        calls += 1
        if calls == 1:
            return ModelResponse(parts=[ToolCallPart("write", {"path": path, "text": "overwrite"})])
        assert messages[-1].parts[0].part_kind == "retry-prompt"
        raise RuntimeError("denied")

    with pytest.raises(RuntimeError, match="denied"):
        await run_authoring_job(authoring_job(tmp_path), model=FunctionModel(respond))
    assert "overwrite" not in (tmp_path / "job/evidence/topic.md").read_text()


async def test_cancelled_job_retains_draft_for_explicit_resume(tmp_path):
    reached_provider = asyncio.Event()
    calls = 0

    async def respond(messages, info):
        nonlocal calls
        calls += 1
        if calls == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "write",
                        {
                            "path": "/draft/topic.md",
                            "text": "A justified conclusion connects evidence to the claim.",
                        },
                    )
                ]
            )
        reached_provider.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(
        run_authoring_job(authoring_job(tmp_path), model=FunctionModel(respond))
    )
    await asyncio.wait_for(reached_provider.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    result = await run_authoring_job(
        authoring_job(tmp_path),
        model=FunctionModel(
            lambda messages, info: ModelResponse(
                parts=[ToolCallPart("final_result", {"ready": True})]
            ),
        ),
    )
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


async def test_repairing_distinct_occurrences_is_not_a_stalled_draft(tmp_path):
    text = "A justified conclusion connects relevant evidence to the claim.\n\n" + "\n\n".join(
        f'<!-- block id="formula-{index}" type="formula" -->\n```math\nx={index}\n```'
        for index in range(3)
    )
    steps = [("write", {"path": "/draft/topic.md", "text": text}), ("validate", {})]
    for index in range(3):
        steps.extend(
            [
                (
                    "edit",
                    {
                        "path": "/draft/topic.md",
                        "old": f'id="formula-{index}" type="formula"',
                        "new": f'id="formula-{index}" type="math"',
                    },
                ),
                ("validate", {}),
            ]
        )
    steps.append(("final_result", {"ready": True}))
    actions = iter(steps)

    def respond(messages, info):
        name, args = next(actions)
        return ModelResponse(parts=[ToolCallPart(name, args)])

    result = await run_authoring_job(authoring_job(tmp_path), model=FunctionModel(respond))
    assert result.metrics.validation_failures == 3
    assert result.metrics.repair_edits == 3
