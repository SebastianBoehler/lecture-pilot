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


def test_orientation_stays_with_exact_target_and_teaching_follows_all_diagnostics():
    from lecturepilot.course_canvas_approved_checkpoints import assemble_approved_checkpoints

    targets = (target(id="t2"), target(id="t3"))
    section = CanvasSection(
        id="s",
        title="Models",
        source_ref="lecture-01.md",
        blocks=[
            CanvasBlock(id="teaching", type="paragraph", text="Source-grounded explanation."),
            CanvasBlock(
                id="check-context-t3", type="paragraph", text="Now justify your comparison."
            ),
            CanvasBlock(id="check-context-t2", type="paragraph", text="First identify the task."),
        ],
    )
    result = assemble_approved_checkpoints(section, targets)
    assert [block.id for block in result.blocks] == [
        "check-context-t2",
        "practice-t2",
        "check-context-t3",
        "practice-t3",
        "teaching",
    ]
    assert [block.text for block in result.blocks if block.type == "checkpoint"] == [
        item.baseline_task for item in targets
    ]
    assert assemble_approved_checkpoints(result, targets) == result


def test_assessment_cannot_be_used_as_orientation():
    from lecturepilot.course_canvas_approved_checkpoints import assemble_approved_checkpoints

    section = CanvasSection(
        id="s",
        title="Models",
        source_ref="lecture-01.md",
        blocks=[CanvasBlock(id="check-context-t2", type="checkpoint", text="An extra task")],
    )
    with pytest.raises(CanvasGenerationRepairableError, match="orientation paragraph"):
        assemble_approved_checkpoints(section, (target(id="t2"),))


def test_duplicate_orientation_is_not_silently_discarded():
    from lecturepilot.course_canvas_approved_checkpoints import assemble_approved_checkpoints

    context = CanvasBlock(id="check-context-t2", type="paragraph", text="Identify the task.")
    section = CanvasSection(
        id="s", title="Models", source_ref="lecture-01.md", blocks=[context, context]
    )
    with pytest.raises(CanvasGenerationRepairableError, match="exactly one orientation"):
        assemble_approved_checkpoints(section, (target(id="t2"),))
