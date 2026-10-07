from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.course_canvas_assessment_normalizer import normalize_section_assessments
from lecturepilot.course_canvas_math import normalize_generated_math, validate_section_math
from test_course_canvas_math import _section_with_math


def test_generated_math_normalization_removes_stray_display_delimiters() -> None:
    formula = r"\begin{aligned}a &= b \\ \[c &= d\end{aligned}"

    normalized = normalize_generated_math(formula)

    assert normalized == r"\begin{aligned}a &= b \\ c &= d\end{aligned}"
    validate_section_math(_section_with_math(normalized))


def test_assessment_only_section_builds_checkpoint_from_selected_grounded_answer() -> None:
    section = CanvasSection(
        id="labels",
        title="Labels",
        source_ref="nested/course/material.pdf page 2",
        blocks=[
            CanvasBlock(
                id="labels-choice",
                type="component",
                text="Which labels are shown?",
                items=[
                    "Hyperparameters; avg acc; retrain with all training data",
                    "Candidate model; score; selected fold",
                ],
                answer_index=0,
                component_id="labels-choice",
                component_type="single_choice_quiz",
                component_ref="components/labels-choice.yaml",
                component_version=1,
                option_ids=["a", "b"],
            )
        ],
    )

    normalized = normalize_section_assessments(section, output_language="en")

    checkpoint = normalized.blocks[-1]
    assert checkpoint.type == "checkpoint"
    assert "Hyperparameters; avg acc" in (checkpoint.text or "")
    assert "List the explicitly named elements" in (checkpoint.text or "")
    assert "relationship" not in (checkpoint.text or "")
