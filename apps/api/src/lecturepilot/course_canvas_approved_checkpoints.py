from collections.abc import Sequence

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_practice_design_models import PracticeDesign, PracticeTarget


def section_practice_targets(
    section: CanvasSection, design: PracticeDesign, extra_blocks: Sequence[CanvasBlock] = ()
) -> tuple[PracticeTarget, ...]:
    """Select only canonical targets already owned by a validated repair scope."""
    ids = {block.id for block in (*section.blocks, *extra_blocks)}
    return tuple(target for target in design.targets if f"practice-{target.id}" in ids)


def assemble_approved_checkpoints(
    section: CanvasSection, targets: Sequence[PracticeTarget]
) -> CanvasSection:
    """Insert professor-owned diagnostics without asking the model to reproduce them."""
    expected = {f"practice-{target.id}": target for target in targets}
    for block in section.blocks:
        if not block.id.startswith("practice-"):
            continue
        target = expected.get(block.id)
        if target is None or block.type != "checkpoint" or block.text != target.baseline_task:
            raise CanvasGenerationRepairableError(
                "Generated content conflicts with the assigned approved practice checkpoints.",
                section_id=section.id,
            )
    checkpoints = [
        CanvasBlock(
            id=checkpoint_id, type="checkpoint", text=target.baseline_task, caption=target.title
        )
        for checkpoint_id, target in expected.items()
    ]
    return section.model_copy(
        update={
            "blocks": checkpoints
            + [block for block in section.blocks if not block.id.startswith("practice-")],
        }
    )
