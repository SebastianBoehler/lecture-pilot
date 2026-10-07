"""Keep validated questions when a bounded repair cannot fix individual items."""

from lecturepilot.practice_exam_models import PracticeExam, PracticeExamQuestion
from lecturepilot.practice_exam_validation import PracticeExamValidationError


def invalidate_exam_questions(exam: PracticeExam, rejected_ids: list[str]) -> PracticeExam:
    if not rejected_ids or not set(rejected_ids) <= {q.id for q in exam.questions}:
        raise PracticeExamValidationError("Question failures must identify exact exam questions.")
    questions = [
        PracticeExamQuestion.model_validate(
            {
                **question.model_dump(),
                "status": "invalid",
                "points": 0,
                "prompt": (
                    "Diese Frage konnte nicht verifiziert werden und wird nicht gewertet."
                    if exam.language == "de"
                    else "This question could not be verified and is not scored."
                ),
                "options": [],
                "answer_index": None,
                "answer_indices": [],
                "reference_answer": None,
                "rubric": [],
            }
        )
        if question.id in rejected_ids
        else question
        for question in exam.questions
    ]
    if not any(q.status == "active" for q in questions):
        raise PracticeExamValidationError("No verified practice exam questions remain.")
    return PracticeExam.model_validate(
        {
            **exam.model_dump(),
            "questions": [q.model_dump() for q in questions],
            "total_points": sum(q.points for q in questions),
        }
    )
