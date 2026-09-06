import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from practice_design_test_helpers import target


def test_backend_assembles_all_assigned_checkpoints_before_generated_instruction():
    from lecturepilot.course_canvas_approved_checkpoints import assemble_approved_checkpoints

    targets = (target(id="t2"), target(id="t3"))
    section = CanvasSection(
        id="s",
        title="Models",
        source_ref="lecture-01.md",
        blocks=[
            CanvasBlock(id="text", type="paragraph", text="Source-grounded explanation."),
        ],
    )
    result = assemble_approved_checkpoints(section, targets)
    assert [block.id for block in result.blocks] == ["practice-t2", "practice-t3", "text"]
    assert [block.text for block in result.blocks[:2]] == [item.baseline_task for item in targets]
    assert [block.id for block in section.blocks] == ["text"]
    assert assemble_approved_checkpoints(result, targets) == result


@pytest.mark.parametrize(
    "block",
    [
        CanvasBlock(id="practice-other", type="checkpoint", text="Unapproved task"),
        CanvasBlock(id="practice-t2", type="checkpoint", text="Mutated task"),
        CanvasBlock(id="practice-t2", type="paragraph", text=target().baseline_task),
    ],
)
def test_assembly_rejects_claimed_unapproved_or_modified_canonical_content(block):
    from lecturepilot.course_canvas_approved_checkpoints import assemble_approved_checkpoints

    section = CanvasSection(id="s", title="Models", source_ref="lecture-01.md", blocks=[block])
    with pytest.raises(CanvasGenerationRepairableError):
        assemble_approved_checkpoints(section, (target(id="t2"),))
