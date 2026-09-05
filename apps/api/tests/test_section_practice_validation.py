import pytest

from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_practice_contract import (
    validate_section_practice,
    section_target_assignments,
)
from lecturepilot.course_canvas_assessment_normalizer import normalize_section_assessments
from test_practice_design_canvas_planner import _source, _design


def test_early_hint_anchor_does_not_move_checkpoint_before_its_learning_outcome():
    source = _source()
    design = _design(source)
    target = design.targets[0]
    early = source.sections[0].model_copy(update={"id": "early"})
    later = early.model_copy(
        update={
            "id": "later",
            "blocks": [
                CanvasBlock(
                    id="notation",
                    type="paragraph",
                    text="The complete notation is introduced here.",
                )
            ],
        }
    )
    target = target.model_copy(
        update={
            "outcome_anchor": target.outcome_anchor.model_copy(
                update={"excerpt": "The complete notation is introduced here."}
            )
        }
    )
    assignments = section_target_assignments(
        design.model_copy(update={"targets": (target,)}), [early, later]
    )
    assert assignments["early"] == ()
    assert assignments["later"] == (target,)


def test_missing_approved_checkpoint_is_rejected_before_section_cache():
    source = _source()
    with pytest.raises(CanvasGenerationRepairableError, match="practice-derive-conclusion"):
        validate_section_practice(source.sections[0], _design(source).targets)


def test_approved_task_text_is_not_rewritten_by_generic_prompt_normalization():
    task = "Two classifiers predict four labels. Compute each error count and justify your choice."
    section = (
        _source()
        .sections[0]
        .model_copy(
            update={"blocks": [CanvasBlock(id="practice-target-1", type="checkpoint", text=task)]}
        )
    )
    normalized = normalize_section_assessments(section, output_language="en")
    assert normalized.blocks[0].text == task


@pytest.mark.parametrize(
    "kind,text", [("paragraph", "Different task."), ("checkpoint", "Different task.")]
)
def test_canonical_id_cannot_bypass_approved_wording_or_block_type(kind, text):
    source = _source()
    design = _design(source)
    section = source.sections[0].model_copy(
        update={"blocks": [CanvasBlock(id="practice-derive-conclusion", type=kind, text=text)]}
    )
    with pytest.raises(CanvasGenerationRepairableError, match="exact approved baseline task"):
        validate_section_practice(section, design.targets)
