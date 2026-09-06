from lecturepilot.assessment_history_models import AssessmentHistoryContext, AssessmentObservation
from lecturepilot.practice_exam_attempts import PracticeAttemptStore
from lecturepilot.practice_exam_store import PracticeExamStore
from lecturepilot.readiness_progress import ReadinessProgressStore
from lecturepilot.storage_layout import StorageLayout


def load_assessment_history(
    layout: StorageLayout,
    *,
    user_id: str,
    course_id: str,
    lecture_id: str,
) -> AssessmentHistoryContext:
    """Read current private records, scoped to this authorized lecture; never copy answer keys."""
    readiness = ReadinessProgressStore(layout).read(user_id=user_id, course_id=course_id)
    observations = [
        AssessmentObservation(
            kind="readiness",
            attempt_id=event.attempt_id,
            question_id=event.question_id,
            created_at=event.created_at,
            section_id=event.section_id,
            assessment=(
                "automatic_choice_check"
                if event.answer_kind == "multiple_choice"
                else "ai_assessment"
            ),
            correct=event.correct,
            score=event.score,
            feedback=event.feedback,
        )
        for event in readiness.attempts
        if event.lecture_id == lecture_id
    ]
    exams = PracticeExamStore(layout)
    attempts = PracticeAttemptStore(exams)
    for exam in exams.list(user_id=user_id, course_id=course_id):
        questions = {
            q.id: q
            for q in exam.questions
            if q.status == "active"
            and all(source.split(":", 1)[0] == lecture_id for source in q.source_ids)
        }
        if not questions:
            continue
        try:
            saved = attempts.list(user_id=user_id, course_id=course_id, exam_id=exam.id)
        except FileNotFoundError:
            continue  # The learner may delete an exam during this read.
        for attempt in saved:
            for question_id, answer in attempt.answers.items():
                question = questions.get(question_id)
                if question is None:
                    continue
                answer_text = answer.text
                if answer.selected_index is not None:
                    answer_text = question.options[answer.selected_index]
                observations.append(
                    AssessmentObservation(
                        kind="practice_exam",
                        attempt_id=str(attempt.id),
                        question_id=question_id,
                        created_at=attempt.created_at.isoformat(),
                        assessment="ungraded",
                        source_revision=attempt.source_revision,
                        source_ids=question.source_ids,
                        prompt=question.prompt[:800],
                        answer=(answer_text or "")[:1600],
                        excerpted=len(question.prompt) > 800 or len(answer_text or "") > 1600,
                    )
                )
    observations.sort(key=lambda item: item.created_at, reverse=True)
    return AssessmentHistoryContext(observations=observations[:12], has_more=len(observations) > 12)
