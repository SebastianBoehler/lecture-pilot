import pytest
from pydantic import ValidationError

from lecturepilot.exam_readiness import ExamReadinessCheck, ExamReadinessCoverage, ExamReadinessQuestion
from lecturepilot.exam_revision_plan import ExamReadinessAnswer, build_exam_revision_plan


def test_revision_plan_marks_wrong_mc_and_keeps_open_answers_for_review() -> None:
    plan = build_exam_revision_plan(
        check=_check(),
        answers=[
            ExamReadinessAnswer(question_id="lecture-03:q1", selected_index=0),
            ExamReadinessAnswer(question_id="lecture-04:q2", text="Risk combines costs and probabilities."),
        ],
    )

    assert plan.score == 0.0
    assert [task.kind for task in plan.tasks] == ["review_wrong_mc", "review_open_answer"]
    assert plan.tasks[0].id == "lecture-03-q1-review"
    assert plan.tasks[0].lecture_id == "lecture-03"
    assert plan.tasks[0].source_ref == "Lecture03-eng.tex frames 5-6"
    assert plan.tasks[0].expected_evidence == "Name evidence as the normalizer."
    assert plan.tasks[0].scaffold_policy is not None
    assert plan.tasks[0].scaffold_policy.profile == "worked_example"
    assert plan.tasks[1].rubric == ["Compare posterior-weighted losses.", "Name one failure mode."]
    assert plan.results[1].status == "needs_rubric_review"


def test_guidance_level_reflects_score_and_repeated_attempts() -> None:
    strong = build_exam_revision_plan(
        check=_check(),
        answers=[
            ExamReadinessAnswer(question_id="lecture-03:q1", selected_index=1),
            ExamReadinessAnswer(question_id="lecture-04:q2", text="Risk combines costs and probabilities."),
        ],
    )
    repeated = build_exam_revision_plan(
        check=_check(),
        answers=[
            ExamReadinessAnswer(question_id="lecture-03:q1", selected_index=1),
            ExamReadinessAnswer(question_id="lecture-04:q2", text="Risk combines costs and probabilities."),
        ],
        previous_attempts=2,
    )

    assert strong.guidance_level == "challenge"
    assert repeated.guidance_level == "scaffolded"


def test_missing_answers_are_rejected() -> None:
    with pytest.raises(ValueError, match="Missing answer"):
        build_exam_revision_plan(check=_check(), answers=[ExamReadinessAnswer(question_id="lecture-03:q1", selected_index=1)])


def test_answer_requires_selection_or_text() -> None:
    with pytest.raises(ValidationError):
        ExamReadinessAnswer(question_id="lecture-03:q1")


def test_revision_task_backfills_scaffold_policy_for_stored_payloads() -> None:
    plan = build_exam_revision_plan(
        check=_check(),
        answers=[
            ExamReadinessAnswer(question_id="lecture-03:q1", selected_index=0),
            ExamReadinessAnswer(question_id="lecture-04:q2", text="Risk combines costs and probabilities."),
        ],
    )
    payload = plan.tasks[0].model_dump(mode="json")
    payload.pop("scaffold_policy")

    task = type(plan.tasks[0]).model_validate(payload)

    assert task.scaffold_policy is not None
    assert task.scaffold_policy.profile == "worked_example"


def _check() -> ExamReadinessCheck:
    return ExamReadinessCheck(
        course_id="demo-ml-course",
        published_lecture_count=2,
        coverage=[
            ExamReadinessCoverage(lecture_id="lecture-03", lecture_title="Bayes", question_count=1),
            ExamReadinessCoverage(lecture_id="lecture-04", lecture_title="Risk", question_count=1),
        ],
        questions=[
            ExamReadinessQuestion(
                id="lecture-03:q1",
                kind="multiple_choice",
                lecture_id="lecture-03",
                lecture_title="Bayes",
                section_id="bayes-formula",
                section_title="Bayes formula",
                prompt="Which term normalizes the posterior?",
                options=["prior", "evidence"],
                answer_index=1,
                rubric=["Name evidence as the normalizer."],
                source_ref="Lecture03-eng.tex frames 5-6",
            ),
            ExamReadinessQuestion(
                id="lecture-04:q2",
                kind="open_ended",
                lecture_id="lecture-04",
                lecture_title="Risk",
                section_id="expected-risk",
                section_title="Expected risk",
                prompt="Explain expected risk.",
                rubric=["Compare posterior-weighted losses.", "Name one failure mode."],
                source_ref="Lecture04-eng.tex frames 8-9",
            ),
        ],
    )
