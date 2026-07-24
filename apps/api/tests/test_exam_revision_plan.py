import pytest
from pydantic import ValidationError

from lecturepilot.exam_readiness import (
    ExamReadinessCheck,
    ExamReadinessCoverage,
    ExamReadinessQuestion,
)
from lecturepilot.exam_answer_evaluation import OpenAnswerEvaluation
from lecturepilot.exam_revision_plan import ExamReadinessAnswer, build_exam_revision_plan


def test_revision_plan_uses_evaluated_open_answer_scores() -> None:
    plan = build_exam_revision_plan(
        check=_check(),
        answers=[
            ExamReadinessAnswer(question_id="lecture-03:q1", selected_index=0),
            ExamReadinessAnswer(
                question_id="lecture-04:q2", text="Risk combines costs and probabilities."
            ),
        ],
        open_evaluations={
            "lecture-04:q2": OpenAnswerEvaluation(
                question_id="lecture-04:q2",
                score=0.75,
                feedback="Good explanation; add one concrete failure mode.",
            )
        },
    )

    assert plan.results[1].score == 0.75
    assert plan.results[1].feedback == "Good explanation; add one concrete failure mode."
    assert plan.results[1].status == "correct"
    assert plan.score == 0.375
    assert [task.kind for task in plan.tasks] == ["review_wrong_mc"]
    assert plan.tasks[0].id == "lecture-03-q1-review"
    assert plan.tasks[0].lecture_id == "lecture-03"
    assert plan.tasks[0].source_ref == "Lecture03-eng.tex frames 5-6"
    assert plan.tasks[0].expected_evidence == "Name evidence as the normalizer."
    assert plan.tasks[0].scaffold_policy is not None
    assert plan.tasks[0].scaffold_policy.profile == "worked_example"


def test_revision_plan_averages_multiple_choice_and_open_answer_scores() -> None:
    plan = build_exam_revision_plan(
        check=_check(),
        answers=[
            ExamReadinessAnswer(question_id="lecture-03:q1", selected_index=1),
            ExamReadinessAnswer(
                question_id="lecture-04:q2", text="Risk combines costs and probabilities."
            ),
        ],
        open_evaluations={
            "lecture-04:q2": OpenAnswerEvaluation(
                question_id="lecture-04:q2",
                score=0.75,
                feedback="Good explanation; add one concrete failure mode.",
            )
        },
    )

    assert plan.results[1].score == 0.75
    assert plan.results[1].status == "correct"
    assert plan.score == 0.875
    assert plan.tasks == []


@pytest.mark.parametrize(
    ("score", "status"),
    [(0.4, "incorrect"), (0.7499, "incorrect"), (0.39, "incorrect")],
)
def test_revision_plan_does_not_create_review_tasks_for_partial_or_incorrect_open_answers(
    score: float,
    status: str,
) -> None:
    plan = build_exam_revision_plan(
        check=_check(),
        answers=[
            ExamReadinessAnswer(question_id="lecture-03:q1", selected_index=1),
            ExamReadinessAnswer(question_id="lecture-04:q2", text="Risk combines costs."),
        ],
        open_evaluations={
            "lecture-04:q2": OpenAnswerEvaluation(
                question_id="lecture-04:q2", score=score, feedback="Review the failure mode."
            )
        },
    )

    assert plan.results[1].status == status
    assert plan.tasks == []


def test_guidance_level_reflects_score_and_repeated_attempts() -> None:
    strong = build_exam_revision_plan(
        check=_check(),
        answers=[
            ExamReadinessAnswer(question_id="lecture-03:q1", selected_index=1),
            ExamReadinessAnswer(
                question_id="lecture-04:q2", text="Risk combines costs and probabilities."
            ),
        ],
        open_evaluations=_open_evaluations(0.75),
    )
    repeated = build_exam_revision_plan(
        check=_check(),
        answers=[
            ExamReadinessAnswer(question_id="lecture-03:q1", selected_index=1),
            ExamReadinessAnswer(
                question_id="lecture-04:q2", text="Risk combines costs and probabilities."
            ),
        ],
        open_evaluations=_open_evaluations(0.75),
        previous_attempts=2,
    )

    assert strong.guidance_level == "challenge"
    assert repeated.guidance_level == "challenge"


def test_missing_answers_are_rejected() -> None:
    with pytest.raises(ValueError, match="Missing answer"):
        build_exam_revision_plan(
            check=_check(),
            answers=[ExamReadinessAnswer(question_id="lecture-03:q1", selected_index=1)],
        )


def test_answer_requires_selection_or_text() -> None:
    with pytest.raises(ValidationError):
        ExamReadinessAnswer(question_id="lecture-03:q1")


def test_revision_task_backfills_scaffold_policy_for_stored_payloads() -> None:
    plan = build_exam_revision_plan(
        check=_check(),
        answers=[
            ExamReadinessAnswer(question_id="lecture-03:q1", selected_index=0),
            ExamReadinessAnswer(
                question_id="lecture-04:q2", text="Risk combines costs and probabilities."
            ),
        ],
        open_evaluations=_open_evaluations(0.75),
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


def _open_evaluations(score: float) -> dict[str, OpenAnswerEvaluation]:
    return {
        "lecture-04:q2": OpenAnswerEvaluation(
            question_id="lecture-04:q2", score=score, feedback="Clear explanation."
        )
    }
