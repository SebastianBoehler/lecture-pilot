from lecturepilot.exam_readiness import build_exam_readiness_check
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
