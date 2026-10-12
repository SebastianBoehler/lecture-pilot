import pytest
from pydantic_ai.models.function import FunctionModel

from lecturepilot.authoring.authoring_job import run_authoring_job
from lecturepilot.canvas.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.authoring.course_canvas_approved_checkpoints import assemble_approved_checkpoints
from lecturepilot.authoring.course_canvas_errors import CanvasGenerationRepairableError
from authoring_test_helpers import markdown
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


async def test_reserved_checkpoint_id_is_retried_with_actionable_feedback(tmp_path):
    job = authoring_job(tmp_path)
    outputs = iter(
        [
            '<!-- block id="practice-transition" type="paragraph" -->\n'
            "A justified conclusion connects relevant evidence to the claim.",
            '<!-- block id="transition-to-practice" type="paragraph" -->\n'
            "A justified conclusion connects relevant evidence to the claim.",
        ]
    )
    feedback = []

    def respond(messages, info):
        if len(messages) > 1:
            feedback.append(str(messages[-1].parts[0].content))
        return markdown(next(outputs))

    result = await run_authoring_job(job, model=FunctionModel(respond))
    assert "practice-transition" in feedback[0] and "Rename" in feedback[0]
    assert result.metrics.validation_failures == 1
    assert result.document.sections[0].blocks[0].text == job.design.targets[0].baseline_task
    assert result.document.sections[0].blocks[1].id == "transition-to-practice"
