from lecturepilot.exam_readiness import build_exam_readiness_check
from lecturepilot.canvas_models import CanvasBlock
from test_exam_readiness import _document


def test_exam_readiness_includes_every_published_lecture_when_course_exceeds_ten() -> None:
    documents = [
        _document(f"lecture-{index:02d}", f"Lecture {index}", with_quiz=True)
        for index in range(1, 14)
    ]
    lectures = [
        type("LectureRecord", (), {"id": document.lecture_id, "title": document.title})()
        for document in documents
    ]

    check = build_exam_readiness_check(
        course_id="demo-ml-course",
        documents=documents,
        lectures=lectures,
    )

    assert len(check.questions) >= 13
    assert all(item.question_count >= 1 for item in check.coverage)
    assert {question.lecture_id for question in check.questions} == {
        document.lecture_id for document in documents
    }
    assert sum(question.kind == "multiple_choice" for question in check.questions) <= 6


def test_exam_readiness_uses_only_standalone_source_assessments() -> None:
    document = _document("lecture-01", "Graph Coverage", with_quiz=True)
    section = document.sections[-1]
    malformed = CanvasBlock(
        id="malformed",
        type="quiz",
        text=(
            "Why this matters: the sheet asks whether complete branch coverage identifies "
            "the failure from Question 4."
        ),
        items=["Yes", "No"],
        answer_index=1,
    )
    labeled = CanvasBlock(
        id="labeled",
        type="quiz",
        text=(
            "Checkpoint: combinational clause coverage Why can "
            "**combinational clause coverage** become impractical?"
        ),
        items=["It requires $2^N$ combinations", "It requires $N$ combinations"],
        answer_index=0,
    )
    document = document.model_copy(
        update={
            "sections": [
                *document.sections[:-1],
                section.model_copy(update={"blocks": [malformed, labeled, *section.blocks]}),
            ]
        }
    )

    check = build_exam_readiness_check(
        course_id="demo-ml-course",
        documents=[document],
        lectures=[
            type("LectureRecord", (), {"id": document.lecture_id, "title": document.title})()
        ],
    )

    prompts = [question.prompt for question in check.questions]
    assert not any(prompt.startswith("Why this matters") for prompt in prompts)
    assert "Why can **combinational clause coverage** become impractical?" in prompts
    assert not any("as you would in an exam answer" in prompt for prompt in prompts)
