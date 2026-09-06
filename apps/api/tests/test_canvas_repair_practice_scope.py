from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.course_canvas_repair_prompt import repair_messages
from lecturepilot.course_practice_design_models import PracticeDesign
from practice_design_test_helpers import proposal, target
from practice_design_review_test_helpers import source_document


def test_whole_section_repair_does_not_request_checkpoints_from_other_sections():
    source = source_document()
    design = PracticeDesign.create(
        **proposal()
        .model_copy(update={"targets": (target(id="first"), target(id="second"))})
        .model_dump(),
        course_id=source.course_id,
        lecture_id=source.lecture_id,
        source_revision="a" * 64,
    )
    section = source.sections[0].model_copy(
        update={
            "blocks": [
                CanvasBlock(
                    id="practice-second", type="checkpoint", text=design.targets[1].baseline_task
                ),
                CanvasBlock(id="instruction", type="paragraph", text="Grounded explanation."),
            ]
        }
    )
    prompt = repair_messages(
        source, section, None, "Missing instruction", practice_design=design, output_language="en"
    )[0]["content"]
    assert "practice-first" not in prompt
    assert "practice-second" in prompt
    assert "server inserts" in prompt.lower()
