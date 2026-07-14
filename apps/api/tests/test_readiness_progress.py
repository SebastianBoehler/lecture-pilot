from lecturepilot.exam_revision_plan import (
    ExamReadinessAttemptResult,
    ExamReadinessQuestionResult,
    ExamRevisionTask,
)
from lecturepilot.readiness_progress import ReadinessProgressStore
from lecturepilot.storage_layout import StorageLayout


def test_progress_store_records_theory_aligned_attempt_events(tmp_path) -> None:
    store = ReadinessProgressStore(StorageLayout(tmp_path))
    result = ExamReadinessAttemptResult(
        course_id="demo-course",
        passing_score=0.7,
        score=0,
        guidance_level="scaffolded",
        results=[
            ExamReadinessQuestionResult(
                question_id="lecture-03:q1",
                kind="multiple_choice",
                lecture_id="lecture-03",
                section_id="risk",
                answer_kind="multiple_choice",
                correct=False,
                selected_index=0,
                correct_index=1,
                status="incorrect",
            )
        ],
        tasks=[
            ExamRevisionTask(
                id="lecture-03-q1-review",
                question_id="lecture-03:q1",
                kind="review_wrong_mc",
                guidance_level="scaffolded",
                lecture_id="lecture-03",
                lecture_title="Risk",
                section_id="risk",
                section_title="Risk",
                prompt="Which quantity should be minimized?",
                rubric=["Name expected risk."],
                expected_evidence="Name expected risk.",
                next_action="Review Risk.",
            )
        ],
    )

    stored = store.record_attempt(user_id="student-a", course_id="demo-course", result=result)
    progress = store.read(user_id="student-a", course_id="demo-course")

    assert stored.attempt_id is not None
    assert store.attempt_count(user_id="student-a", course_id="demo-course") == 1
    assert progress.attempts[0].first_try is True
    assert progress.attempts[0].task_id == "lecture-03-q1-review"
    assert progress.active_tasks[0].expected_evidence == "Name expected risk."
