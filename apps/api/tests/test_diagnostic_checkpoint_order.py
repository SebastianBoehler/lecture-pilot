import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_validation import validate_section_assessments
from lecturepilot.learning_design_report import _worked_example_diagnostics


def section(*blocks: CanvasBlock) -> CanvasSection:
    return CanvasSection(id="topic", title="Topic", blocks=list(blocks))


def test_approved_diagnostic_can_precede_help_and_a_formative_check() -> None:
    validate_section_assessments(
        section(
            CanvasBlock(id="practice-target", type="checkpoint", text="Exact approved diagnostic."),
            CanvasBlock(id="worked-example-topic", type="paragraph", text="An analogous example."),
            CanvasBlock(
                id="formative", type="checkpoint", text="Explain the result for a new case."
            ),
        )
    )


def test_example_after_an_ordinary_formative_check_remains_invalid() -> None:
    with pytest.raises(CanvasGenerationRepairableError, match="before"):
        validate_section_assessments(
            section(
                CanvasBlock(
                    id="formative", type="checkpoint", text="Explain the result for a new case."
                ),
                CanvasBlock(
                    id="worked-example-topic", type="paragraph", text="An analogous example."
                ),
            )
        )


def test_publication_report_does_not_reject_help_after_an_approved_diagnostic() -> None:
    candidate = section(
        CanvasBlock(id="practice-target", type="checkpoint", text="Exact approved diagnostic."),
        CanvasBlock(id="worked-example-topic", type="paragraph", text="An analogous example."),
        CanvasBlock(id="formative", type="checkpoint", text="Explain the result for a new case."),
    )
    assert _worked_example_diagnostics(candidate) == []
