import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.authoring_job import run_authoring_job
from lecturepilot.authoring_models import AuthoringStalledError
from lecturepilot.authoring_state import load_state
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.course_canvas_approved_checkpoints import assemble_approved_checkpoints
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from practice_design_test_helpers import target
from test_authoring_job import authoring_job


@pytest.mark.parametrize(
    ("block", "instruction"),
    [
        (CanvasBlock(id="practice-transition", type="paragraph", text="Now apply it."), "Rename"),
        (CanvasBlock(id="practice-other", type="checkpoint", text="Unapproved"), "Remove"),
        (CanvasBlock(id="practice-t2", type="checkpoint", text="Modified"), "Remove"),
    ],
)
def test_checkpoint_conflict_identifies_block_and_safe_repair(block, instruction):
    section = CanvasSection(id="topic", title="Evidence", blocks=[block])
    with pytest.raises(CanvasGenerationRepairableError) as caught:
        assemble_approved_checkpoints(section, (target(id="t2"),))
    error = caught.value
    assert error.section_id == "topic"
    assert error.block_id == block.id
    assert block.id in str(error)
    assert instruction in str(error)
    assert "server" in str(error)
    assert section.blocks == [block]


async def test_stalled_checkpoint_repair_resumes_with_actionable_feedback(tmp_path):
    job = authoring_job(tmp_path)
    steps = iter(
        [
            (
                "write",
                {
                    "path": "/draft/topic.md",
                    "text": (
                        '<!-- block id="practice-transition" type="paragraph" -->\n'
                        "A justified conclusion connects relevant evidence to the claim."
                    ),
                },
            ),
            ("validate", {}),
            ("validate", {}),
            ("validate", {}),
        ]
    )

    def stalled(messages, info):
        name, args = next(steps)
        return ModelResponse(parts=[ToolCallPart(name, args)])

    with pytest.raises(AuthoringStalledError) as stopped:
        await run_authoring_job(job, model=FunctionModel(stalled))
    assert "/draft/topic.md" in str(stopped.value)
    assert "practice-transition" in str(stopped.value)
    assert "Rename" in str(stopped.value)
    before = load_state(job)
    assert max(before.failures.values()) == 3
    resumed_steps = iter(
        [
            ("validate", {}),
            (
                "edit",
                {
                    "path": "/draft/topic.md",
                    "old": 'id="practice-transition"',
                    "new": 'id="transition-to-practice"',
                },
            ),
            ("validate", {}),
            ("final_result", {"ready": True}),
        ]
    )
    calls = 0

    def repair(messages, info):
        nonlocal calls
        calls += 1
        if calls == 2:
            feedback = str(messages[-1].parts[0].content)
            assert "/draft/topic.md" in feedback
            assert "practice-transition" in feedback
            assert "Rename" in feedback
        name, args = next(resumed_steps)
        return ModelResponse(parts=[ToolCallPart(name, args)])

    result = await run_authoring_job(job, model=FunctionModel(repair))
    assert result.metrics.resumes == 1
    assert result.metrics.validation_failures == before.metrics.validation_failures + 1
    assert result.metrics.repair_edits == 1
    assert result.document.sections[0].blocks[0].text == job.design.targets[0].baseline_task
    assert result.document.sections[0].blocks[1].id == "transition-to-practice"


async def test_explicit_retry_still_stops_after_three_unchanged_failures(tmp_path):
    job = authoring_job(tmp_path)

    def no_repair(messages, info):
        return ModelResponse(parts=[ToolCallPart("validate", {})])

    for attempt in range(2):
        with pytest.raises(AuthoringStalledError):
            await run_authoring_job(job, model=FunctionModel(no_repair))
        assert load_state(job).metrics.validation_failures == 3 * (attempt + 1)
