from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lecturepilot.practice_exam_models import PracticeExam, PracticeExamQuestion
from lecturepilot.practice_exam_validation import (
    PracticeExamValidationError,
    validate_practice_exam,
)


def test_validator_accepts_grounded_mixed_exam() -> None:
    exam = _exam()

    validate_practice_exam(
        exam,
        authoritative_source_ids={"lecture-01:risk"},
        question_count=20,
        selected_ppi_source_ids={"ppi-42"},
    )


def test_validator_requires_requested_count_and_unique_prompts() -> None:
    exam = _exam()
    exam.questions[1].prompt = exam.questions[0].prompt.upper()

    with pytest.raises(PracticeExamValidationError, match="unique prompts"):
        validate_practice_exam(
            exam,
            authoritative_source_ids={"lecture-01:risk"},
            question_count=20,
        )
    with pytest.raises(PracticeExamValidationError, match="requested 21"):
        validate_practice_exam(
            _exam(),
            authoritative_source_ids={"lecture-01:risk"},
            question_count=21,
        )


def test_validator_rejects_unknown_or_ppi_only_course_anchor() -> None:
    exam = _exam()
    exam.questions[0].source_ids = ["ppi-42"]
    exam.questions[0].ppi_pattern_ids = ["ppi-42"]

    with pytest.raises(PracticeExamValidationError, match="course source"):
        validate_practice_exam(
            exam,
            authoritative_source_ids={"lecture-01:risk"},
            question_count=20,
            selected_ppi_source_ids={"ppi-42"},
        )


def test_validator_rejects_unselected_ppi_pattern() -> None:
    exam = _exam()
    exam.questions[0].ppi_pattern_ids = ["ppi-99"]

    with pytest.raises(PracticeExamValidationError, match="unselected PPI"):
        validate_practice_exam(
            exam,
            authoritative_source_ids={"lecture-01:risk"},
            question_count=20,
            selected_ppi_source_ids={"ppi-42"},
        )


def test_validator_requires_coverage_of_every_available_lecture() -> None:
    with pytest.raises(PracticeExamValidationError, match="every available lecture"):
        validate_practice_exam(
            _exam(),
            authoritative_source_ids={"lecture-01:risk", "lecture-02:generalization"},
            question_count=20,
            selected_ppi_source_ids={"ppi-42"},
        )


def test_validator_rejects_copied_protocol_excerpt() -> None:
    excerpt = (
        "This unusually specific protocol sentence describes every hidden detail of the old exam "
        "question and must never be reproduced verbatim by the generated practice exam."
    )
    exam = _exam()
    exam.questions[0].prompt = excerpt

    with pytest.raises(PracticeExamValidationError, match="copies retained PPI text"):
        validate_practice_exam(
            exam,
            authoritative_source_ids={"lecture-01:risk"},
            question_count=20,
            selected_ppi_source_ids={"ppi-42"},
            ppi_texts=[excerpt],
        )


def _exam() -> PracticeExam:
    questions = []
    for index in range(1, 21):
        questions.append(
            PracticeExamQuestion(
                id=f"q-{index:02d}",
                kind="multiple_choice" if index % 2 else "open_ended",
                prompt=f"Question {index}: apply empirical risk to a distinct scenario?",
                points=2,
                difficulty="standard",
                options=["One", "Two", "Three", "Four"] if index % 2 else [],
                answer_index=1 if index % 2 else None,
                rubric=[] if index % 2 else ["Defines risk", "Applies it"],
                source_ids=["lecture-01:risk"],
                ppi_pattern_ids=["ppi-42"] if index == 2 else [],
            )
        )
    return PracticeExam(
        id="a" * 32,
        course_id="martius-ml",
        title="Practice exam",
        language="en",
        instructions=["Answer every question."],
        duration_minutes=90,
        created_at=datetime.now(UTC),
        total_points=40,
        source_revision="b" * 64,
        source_ids=["lecture-01:risk"],
        ppi_source_ids=["ppi-42"],
        questions=questions,
    )
