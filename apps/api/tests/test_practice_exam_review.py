from copy import deepcopy

import pytest

from lecturepilot.practice_exam_prompt import practice_exam_review_messages
from lecturepilot.practice_exam_validation import (
    PracticeExamValidationError,
    validate_practice_exam_review,
)
from test_practice_exam_validation import _exam


EVIDENCE = "[lecture-01:risk] Risk is expected loss. Empirical risk averages sample loss."


def _review():
    return {
        "reviews": [
            {
                "question_id": q.id,
                "verdict": "pass",
                "issue": "",
                "source_ids": q.source_ids,
                "solved_answer_index": q.answer_index,
                "reasoning": "The definition supports this answer.",
                "evidence_quotes": [
                    {"source_id": "lecture-01:risk", "quote": "Risk is expected loss."}
                ],
            }
            for q in _exam().questions
        ]
    }


def _validate(payload):
    validate_practice_exam_review(
        payload,
        exam=_exam(),
        authoritative_source_ids={"lecture-01:risk"},
        course_evidence=EVIDENCE,
    )


def test_review_accepts_verified_quotes_and_independent_keys():
    _validate(_review())


@pytest.mark.parametrize(
    "change,match",
    [
        ({"solved_answer_index": 0}, "independently solved answer"),
        ({"solved_answer_index": True}, "independently solved answer"),
        ({"evidence_quotes": []}, "source quotation"),
        (
            {"evidence_quotes": [{"source_id": "lecture-01:risk", "quote": "invented evidence"}]},
            "quotation",
        ),
        ({"reasoning": " "}, "reasoning"),
        ({"issue": "This is actually ambiguous."}, "contradictory"),
    ],
)
def test_review_rejects_unsupported_pass(change, match):
    payload = _review()
    payload["reviews"][0].update(change)
    with pytest.raises(PracticeExamValidationError, match=match):
        _validate(payload)


def test_review_rejects_quote_from_another_source():
    payload = _review()
    payload["reviews"][0]["evidence_quotes"][0]["source_id"] = "lecture-02:other"
    with pytest.raises(PracticeExamValidationError, match="quotation"):
        validate_practice_exam_review(
            payload,
            exam=_exam(),
            authoritative_source_ids={"lecture-01:risk", "lecture-02:other"},
            course_evidence=EVIDENCE + "\n[lecture-02:other] Risk is expected loss.",
        )


def test_review_rejects_bare_pass_from_old_contract():
    payload = _review()
    for item in payload["reviews"]:
        for field in ["reasoning", "evidence_quotes", "solved_answer_index"]:
            del item[field]
    with pytest.raises(PracticeExamValidationError):
        _validate(payload)


def test_review_rejects_extra_malformed_entry():
    payload = _review()
    payload["reviews"].append(None)
    with pytest.raises(PracticeExamValidationError, match="every question once"):
        _validate(payload)


def test_review_prompt_hides_multiple_choice_keys():
    exam = _exam()
    before = deepcopy(exam)
    messages = practice_exam_review_messages(course_evidence=EVIDENCE, exam=exam)
    import json

    candidate = json.loads(messages[1]["content"].split("Candidate exam", 1)[1].split("\n", 1)[1])
    for question in candidate["questions"]:
        assert "answer_index" not in question
    assert exam == before
