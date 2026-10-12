from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.course_canvas_practice_contract import section_target_assignments
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
