from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import ValidationError

from lecturepilot.practice_exam_attempts import PracticeAttemptStore, PracticeSubmission
from lecturepilot.practice_exam_models import (
    PracticeExamQuestion,
    practice_exam_solution_sheet,
    public_practice_exam,
)
from lecturepilot.practice_exam_prompt import practice_exam_review_messages
from lecturepilot.practice_exam_solution_latex import render_practice_exam_solution_tex
from lecturepilot.practice_exam_store import PracticeExamStore
from lecturepilot.practice_exam_validation import (
    PracticeExamValidationError,
    validate_practice_exam_review,
)
from lecturepilot.storage_layout import StorageLayout
from test_practice_exam_review import EVIDENCE, _review
from test_practice_exam_validation import _exam


def multi_question(**updates):
    return PracticeExamQuestion(
        **{
            "id": "q-01",
            "kind": "multiple_select",
            "prompt": "Select every true statement about risk.",
            "points": 2,
            "difficulty": "standard",
            "options": [
                "Expected loss",
                "Sample average for empirical risk",
                "Always zero",
                "A count",
            ],
            "answer_indices": [0, 1],
            "source_ids": ["lecture-01:risk"],
            **updates,
        }
    )


def multi_exam():
    exam = _exam()
    questions = [multi_question(), *exam.questions[1:]]
    return exam.model_copy(
        update={"questions": questions, "total_points": sum(q.points for q in questions)}
    )


@pytest.mark.parametrize(
    "updates",
    [
        {"answer_indices": []},
        {"answer_indices": [0, 0]},
        {"answer_indices": [0, 4]},
        {"answer_indices": [True, 1]},
        {"answer_index": 0},
        {"options": ["a", "b", "c"]},
    ],
)
def test_multiple_select_rejects_invalid_keys_and_shape(updates):
    with pytest.raises(ValidationError):
        multi_question(**updates)


def test_multiple_select_keys_stay_private_and_solutions_include_all_answers():
    exam = multi_exam()
    instructions = public_practice_exam(exam).instructions
    assert any("complete correct set" in line for line in instructions)
    question = public_practice_exam(exam).questions[0].model_dump()
    assert "answer_indices" not in question
    assert "answer_index" not in question
    assert practice_exam_solution_sheet(exam).questions[0].answer_indices == [0, 1]
    candidate = practice_exam_review_messages(course_evidence=EVIDENCE, exam=exam)[1]["content"]
    assert '"answer_indices"' not in candidate
    assert '"answer_index"' not in candidate
    tex = render_practice_exam_solution_tex(exam)
    assert "Correct answers: A, B." in tex
    assert "Negative scores are possible" in tex


@pytest.mark.parametrize("indices", [[0], [0, 2], [0, 1, 1], [True, 1], None])
def test_independent_review_rejects_incomplete_wrong_or_malformed_multiple_keys(indices):
    payload = deepcopy(_review())
    payload["reviews"][0].update(solved_answer_index=None, solved_answer_indices=indices)
    with pytest.raises(PracticeExamValidationError, match="independently solved answer"):
        validate_practice_exam_review(
            payload,
            exam=multi_exam(),
            authoritative_source_ids={"lecture-01:risk"},
            course_evidence=EVIDENCE,
        )


def test_independent_review_accepts_same_complete_answer_set_in_any_order():
    payload = _review()
    payload["reviews"][0].update(solved_answer_index=None, solved_answer_indices=[1, 0])
    validate_practice_exam_review(
        payload,
        exam=multi_exam(),
        authoritative_source_ids={"lecture-01:risk"},
        course_evidence=EVIDENCE,
    )


@pytest.mark.asyncio
async def test_planner_generates_selected_format_and_repairs_a_wrong_multiple_answer_key():
    from practice_exam_planner_fixtures import (
        _ModelClient,
        _Registry,
        _payload,
        _plan_args,
        _review_payload,
        _solution_review_payload,
    )
    from lecturepilot.practice_exam_planner import PracticeExamPlanner

    payload = _payload()
    review = _review_payload()
    for q, r in zip(payload["questions"], review["reviews"], strict=True):
        if q["kind"] == "multiple_choice":
            q.update(
                kind="multiple_select",
                options=["Expected loss", "Empirical sample average", "Always zero", "A count"],
                answer_index=None,
                answer_indices=[0, 1],
                points=2,
            )
            r.update(solved_answer_index=None, solved_answer_indices=[1, 0])
    wrong = deepcopy(payload)
    wrong["questions"][0]["answer_indices"] = [0, 2]
    repairs = deepcopy(payload)
    repairs["questions"] = repairs["questions"][:1]
    client = _ModelClient([wrong, review, repairs, review, _solution_review_payload()])
    exam = await PracticeExamPlanner(provider_registry=_Registry(), model_client=client).plan(
        **_plan_args(), choice_format="multiple_answers"
    )
    assert exam.questions[0].answer_indices == [0, 1]
    assert client.calls == 5
    assert "exactly four" in client.messages[0][0]["content"]
    assert "independently solved answers" in client.messages[2][0]["content"]


def test_multiple_selections_persist_immutably_without_grading(tmp_path):
    exams = PracticeExamStore(StorageLayout(tmp_path))
    exam = multi_exam()
    exams.write(user_id="student-demo", course_id=exam.course_id, exam=exam)
    attempts = PracticeAttemptStore(exams)
    submission = PracticeSubmission(id=uuid4(), answers={"q-01": {"selected_indices": [0, 2]}})
    saved = attempts.save(
        user_id="student-demo", course_id=exam.course_id, exam_id=exam.id, submission=submission
    )
    assert saved.answers["q-01"].selected_indices == [0, 2]
    assert saved.assessment == "ungraded"
    assert (
        attempts.list(user_id="student-demo", course_id=exam.course_id, exam_id=exam.id)[0] == saved
    )
    for answer in [
        {"selected_indices": [4]},
        {"selected_indices": [0, 0]},
        {"selected_index": 0},
        {"text": "a"},
    ]:
        with pytest.raises(ValueError):
            attempts.save(
                user_id="student-demo",
                course_id=exam.course_id,
                exam_id=exam.id,
                submission=PracticeSubmission(id=uuid4(), answers={"q-01": answer}),
            )


def test_fixed_multiple_select_points_hide_answer_count_without_mutating_legacy_exam():
    from lecturepilot.practice_exam_latex import render_practice_exam_tex

    exam = multi_exam()
    for indices in ([0], [0, 1], [0, 1, 2, 3]):
        exam.questions[0] = multi_question(points=len(indices), answer_indices=indices)
        exam.total_points = sum(q.points for q in exam.questions)
        public = public_practice_exam(exam)
        assert public.questions[0].points == 4
        assert public.total_points == sum(q.points for q in public.questions)
        assert practice_exam_solution_sheet(exam).questions[0].points == 4
        assert exam.questions[0].points == len(indices)
        assert "4 points" in render_practice_exam_tex(public)


def test_open_answer_review_is_blind():
    candidate = practice_exam_review_messages(course_evidence=EVIDENCE, exam=multi_exam())[1][
        "content"
    ]
    assert '"reference_answer"' not in candidate
    assert '"rubric"' not in candidate


def test_german_exam_labels():
    from lecturepilot.practice_exam_latex import render_practice_exam_tex

    exam = multi_exam().model_copy(update={"language": "de"})
    tex = render_practice_exam_tex(public_practice_exam(exam))
    solutions = render_practice_exam_solution_tex(exam)
    assert "Dauer:" in tex and "Aufgabe 1" in tex and "Punkte" in tex
    assert "Lösungen" in solutions and "Richtige Antworten" in solutions
    assert "Musterantwort" in solutions and "Bewertungskriterien" in solutions
