import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
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


@pytest.mark.parametrize(
    ("block", "message"),
    [
        (
            CanvasBlock(
                id="quiz",
                type="quiz",
                text=(
                    "Why this matters: the sheet asks whether coverage identifies "
                    "the failure from Question 4."
                ),
                items=["Yes", "No"],
                answer_index=1,
            ),
            "understandable without",
        ),
        (
            CanvasBlock(
                id="quiz",
                type="quiz",
                text="Checkpoint: coverage Why can **path coverage** become impractical?",
                items=["Loops create many paths", "Branches never execute"],
                answer_index=0,
            ),
            "labels in caption",
        ),
        (
            CanvasBlock(
                id="checkpoint",
                type="checkpoint",
                text="Explain the key mechanism in **Testing Basics** in your own words.",
            ),
            "specific source-grounded task",
        ),
    ],
)
def test_canvas_validation_rejects_contextless_or_generic_assessments(
    block: CanvasBlock, message: str
) -> None:
    source = _document(_quiz(answer_index=1))
    candidate = _document(_quiz(answer_index=1))
    section = candidate.sections[0]
    candidate = candidate.model_copy(
        update={"sections": [section.model_copy(update={"blocks": [*section.blocks, block]})]}
    )

    with pytest.raises(CanvasGenerationRepairableError, match=message):
        validate_planned_document(candidate, source)


@pytest.mark.parametrize(
    "prompt",
    [
        (
            "Match each testing question to its classification dimension: "
            "test level, test method, or test criterion."
        ),
        (
            "For a BankAccount with a balance of 100, write three test ideas for "
            "withdraw(int amount) and state each expected result."
        ),
        (
            "Complete the statement: The basic functional-safety norm is IEC ____; "
            "the road-vehicle norm is ISO ____."
        ),
        "List the clauses in `(a > b) && ready` without including logical operators.",
    ],
)
def test_canvas_validation_accepts_a_concrete_task(prompt: str) -> None:
    source = _document(_quiz(answer_index=1))
    candidate = _document(_quiz(answer_index=1))
    section = candidate.sections[0]
    matching = CanvasBlock(
        id="matching-checkpoint",
        type="checkpoint",
        text=prompt,
    )
    candidate = candidate.model_copy(
        update={"sections": [section.model_copy(update={"blocks": [*section.blocks, matching]})]}
    )

    validate_planned_document(candidate, source)


def test_canvas_validation_accepts_a_question_with_a_short_context_clause() -> None:
    source = _document(_quiz(answer_index=1))
    candidate = _document(
        CanvasBlock(
            id="context-question",
            type="quiz",
            text="In Java, what happens when a switch case does not contain `break`?",
            items=["Execution falls through.", "The method returns."],
            answer_index=0,
        )
    )

    validate_planned_document(candidate, source)


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
