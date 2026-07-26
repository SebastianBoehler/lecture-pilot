import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_enrichment import enrich_learning_document
from lecturepilot.course_canvas_plan_parser import planned_document
from lecturepilot.course_canvas_validation import validate_planned_document


def test_planner_rejects_quiz_without_an_explicit_answer_index() -> None:
    source = _document(_quiz(answer_index=1))
    payload = {
        "title": "Generated lecture",
        "sections": [
            {
                "id": "generated-topic",
                "title": "Generated topic",
                "source_ref": "lecture.pdf page 1",
                "blocks": [
                    {
                        "id": "quiz",
                        "type": "quiz",
                        "text": "Which statement follows from the lecture?",
                        "items": ["Unsupported statement", "Source-backed statement"],
                    }
                ],
            }
        ],
    }

    with pytest.raises(CanvasGenerationRepairableError, match="explicit answer_index"):
        planned_document(payload, source)


def test_canvas_validation_rejects_quiz_without_two_options() -> None:
    source = _document(_quiz(answer_index=1))
    candidate = _document(
        CanvasBlock(
            id="quiz",
            type="quiz",
            text="Which statement follows from the lecture?",
            items=["Only one option"],
            answer_index=0,
        )
    )

    with pytest.raises(CanvasGenerationRepairableError, match="at least 2 answer options"):
        validate_planned_document(candidate, source)


def test_enrichment_does_not_invent_a_quiz_or_answer_key() -> None:
    document = _document_without_quiz()

    enriched = enrich_learning_document(document)

    assert all(block.type != "quiz" for section in enriched.sections for block in section.blocks)


def _quiz(*, answer_index: int) -> CanvasBlock:
    return CanvasBlock(
        id="quiz",
        type="quiz",
        text="Which statement follows from the lecture?",
        items=["Unsupported statement", "Source-backed statement"],
        answer_index=answer_index,
    )


def _document(quiz: CanvasBlock) -> CanvasDocument:
    teaching = [
        CanvasBlock(
            id=f"paragraph-{index}",
            type="paragraph",
            text=(
                "This source-backed explanation describes the concept, its mechanism, "
                "a concrete application, and a failure mode in enough detail for study. "
            )
            * 2,
        )
        for index in range(1, 5)
    ]
    return CanvasDocument(
        id="course-lecture",
        course_id="course",
        lecture_id="lecture",
        title="Lecture",
        source_kind="generated",
        source_ref="lecture.pdf",
        workspace_path="canvas/index.md",
        sections=[
            CanvasSection(
                id="topic",
                title="Topic",
                source_ref="lecture.pdf page 1",
                blocks=[*teaching, quiz],
            )
        ],
    )


def _document_without_quiz() -> CanvasDocument:
    document = _document(_quiz(answer_index=1))
    section = document.sections[0]
    return document.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={"blocks": [block for block in section.blocks if block.type != "quiz"]}
                )
            ]
        }
    )
