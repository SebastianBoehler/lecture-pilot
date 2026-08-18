from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.course_canvas_section_planner import _read_section_payload
from lecturepilot.course_canvas_validation import validate_section_assessments


def test_section_parser_turns_a_declarative_checkpoint_into_a_concrete_task() -> None:
    section = _source_section()

    parsed = _read_section_payload(
        {
            "title": "Probability",
            "blocks": [
                {"type": "paragraph", "text": "Probability separates evidence from causes."},
                {
                    "type": "checkpoint",
                    "text": (
                        "Why this matters: probability-based reasoning separates observable "
                        "evidence from hidden causes."
                    ),
                },
            ],
        },
        section,
        {},
    )

    validate_section_assessments(parsed)
    checkpoint = next(block for block in parsed.blocks if block.type == "checkpoint")
    assert checkpoint.text == (
        "Explain this statement and identify the relationship it describes: "
        "probability-based reasoning separates observable evidence from hidden causes."
    )


def test_section_parser_adds_a_grounded_checkpoint_when_one_is_missing() -> None:
    section = _source_section()

    parsed = _read_section_payload(
        {
            "title": "Probability",
            "blocks": [
                {
                    "type": "paragraph",
                    "text": "A posterior combines the prior with observed evidence.",
                }
            ],
        },
        section,
        {},
    )

    validate_section_assessments(parsed)
    checkpoint = next(block for block in parsed.blocks if block.type == "checkpoint")
    assert checkpoint.text == (
        "Explain this statement and identify the relationship it describes: "
        "A posterior combines the prior with observed evidence."
    )


def test_section_repair_uses_original_evidence_when_patch_only_contains_math() -> None:
    parsed = _read_section_payload(
        {
            "title": "Probability",
            "blocks": [{"type": "math", "text": r"P(C\mid x)=P(C)p(x\mid C)/p(x)"}],
        },
        _source_section(),
        {},
    )

    validate_section_assessments(parsed)
    checkpoint = next(block for block in parsed.blocks if block.type == "checkpoint")
    assert checkpoint.text == (
        "Explain this statement and identify the relationship it describes: "
        "this statement summarizes how probability combines prior beliefs and observations."
    )


def _source_section() -> CanvasSection:
    return CanvasSection(
        id="probability",
        title="Probability",
        source_ref="nested/lecture.pdf pages 1-2",
        blocks=[
            CanvasBlock(
                id="source",
                type="paragraph",
                text=(
                    "This slide summarizes how probability combines prior beliefs and observations."
                ),
            )
        ],
    )
