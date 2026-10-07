import pytest

from lecturepilot.assessment_prompts import readiness_prompt
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.course_canvas_practice_contract import practice_prompt_instruction
from lecturepilot.course_canvas_validation import validate_section_assessments
from lecturepilot.course_teaching_instructions import canvas_teaching_instruction
from lecturepilot.learning_design_report import _concept_report
from lecturepilot.learning_map_models import LearningMapNode
from practice_design_test_helpers import practice_design_for_canvas
from practice_design_review_test_helpers import source_document


@pytest.mark.parametrize(
    "prompt",
    [
        "Begründe, warum die Entscheidung korrekt ist.",
        "Zeige, wie sich die Fehlerkosten auswirken.",
        "Gib an, welche Voraussetzung benötigt wird.",
    ],
)
def test_german_assessment_verbs_are_valid_readiness_tasks(prompt):
    assert readiness_prompt(prompt, "checkpoint") == prompt


def test_authoring_receives_approved_misconceptions_without_hidden_tasks():
    design = practice_design_for_canvas(source_document())
    prompt = practice_prompt_instruction(design)
    misconception = design.targets[0].misconceptions[0]
    assert misconception.description in prompt
    assert misconception.diagnostic_cue in prompt
    assert design.targets[0].independent_exit_task not in prompt
    assert design.targets[0].delayed_transfer_task not in prompt


def test_administrative_section_does_not_require_filler_checkpoint():
    section = CanvasSection(
        id="admin",
        title="Course organization",
        source_ref="info.md",
        blocks=[
            CanvasBlock(id="admin-text", type="paragraph", text="Submit coursework before Friday."),
        ],
    )
    validate_section_assessments(section)
    node = LearningMapNode(
        id="admin",
        title=section.title,
        lecture_id="lecture-1",
        section_id=section.id,
        source_ref=section.source_ref,
        prerequisites=[],
        gate_ids=[],
        quiz_ids=[],
    )
    _, diagnostics = _concept_report(section=section, node=node)
    assert diagnostics == []


def test_authoring_prompt_explains_worked_example_identity_for_validation():
    assert "worked-example-" in canvas_teaching_instruction()
