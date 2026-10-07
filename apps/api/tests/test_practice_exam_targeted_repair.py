from copy import deepcopy

import pytest
from practice_exam_planner_fixtures import (
    _ModelClient,
    _Registry,
    _payload,
    _plan_args,
    _review_payload,
    _solution_review_payload,
)
from lecturepilot.practice_exam_planner import PracticeExamPlanner


@pytest.mark.asyncio
async def test_repairs_all_rejected_ids_and_preserves_every_passing_question():
    original = _payload()
    failed = _review_payload()
    for index in (0, 2):
        failed["reviews"][index].update(verdict="fail", issue="Ambiguous premise")
    repairs = deepcopy(original)
    repairs["questions"] = [repairs["questions"][0], repairs["questions"][2]]
    repairs["questions"][0]["prompt"] = "A repaired unambiguous risk question?"
    client = _ModelClient(
        [original, failed, repairs, _review_payload(), _solution_review_payload()]
    )
    exam = await PracticeExamPlanner(provider_registry=_Registry(), model_client=client).plan(
        **_plan_args()
    )
    assert exam.questions[0].prompt == repairs["questions"][0]["prompt"]
    assert exam.questions[1].prompt == original["questions"][1]["prompt"]
    assert (
        client.response_formats[2]["json_schema"]["schema"]["properties"]["questions"]["maxItems"]
        == 2
    )
    repair_message = client.messages[2][1]["content"]
    assert "Previous candidate" in repair_message
    assert "q-01" in repair_message and "q-03" in repair_message
    assert "Write exactly 2 questions" in client.messages[2][0]["content"]
    assert "Write exactly 20 questions" not in client.messages[2][0]["content"]


async def test_failed_final_review_invalidates_only_rejected_questions():
    original = _payload()
    failed = _review_payload()
    failed["reviews"][0].update(verdict="fail", issue="Unsupported premise")
    repairs = deepcopy(original)
    repairs["questions"] = repairs["questions"][:1]
    client = _ModelClient([original, failed, repairs, failed, _solution_review_payload()])
    exam = await PracticeExamPlanner(provider_registry=_Registry(), model_client=client).plan(
        **_plan_args()
    )
    assert exam.questions[0].status == "invalid"
    assert exam.questions[0].points == 0
    assert not exam.questions[0].options and exam.questions[0].answer_index is None
    assert exam.total_points == 38
    assert [q.prompt for q in exam.questions[1:]] == [
        q["prompt"] for q in original["questions"][1:]
    ]


@pytest.mark.asyncio
async def test_question_shape_repair_receives_prior_candidate_and_only_failed_id():
    original = _payload()
    del original["questions"][0]["prompt"]
    repairs = _payload()
    repairs["questions"] = repairs["questions"][:1]
    client = _ModelClient([original, repairs, _review_payload(), _solution_review_payload()])
    exam = await PracticeExamPlanner(provider_registry=_Registry(), model_client=client).plan(
        **_plan_args()
    )
    assert len(exam.questions) == 20
    assert (
        client.response_formats[1]["json_schema"]["schema"]["properties"]["questions"]["maxItems"]
        == 1
    )


@pytest.mark.asyncio
async def test_open_answer_sheet_review_repairs_only_rejected_reference_answer():
    original = _payload()
    failed = _solution_review_payload()
    failed["reviews"][0].update(verdict="fail", issue="Reference answer contradicts blind solution")
    repairs = deepcopy(original)
    repairs["questions"] = [repairs["questions"][1]]
    repairs["questions"][0]["reference_answer"] = "A corrected full-credit answer."
    client = _ModelClient(
        [
            original,
            _review_payload(),
            failed,
            repairs,
            _review_payload(),
            _solution_review_payload(),
        ]
    )
    exam = await PracticeExamPlanner(provider_registry=_Registry(), model_client=client).plan(
        **_plan_args()
    )
    assert exam.questions[1].reference_answer == "A corrected full-credit answer."
    assert (
        client.response_formats[3]["json_schema"]["schema"]["properties"]["questions"]["maxItems"]
        == 1
    )
    assert "Independently derived blind solutions" in client.messages[2][1]["content"]
    assert "Reference answer contradicts" in client.messages[3][0]["content"]
