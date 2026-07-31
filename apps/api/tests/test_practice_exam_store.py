from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from lecturepilot.practice_exam_models import (
    PracticeExam,
    PracticeExamGenerationInput,
    PracticeExamQuestion,
    public_practice_exam,
)
from lecturepilot.practice_exam_store import PracticeExamStore
from lecturepilot.storage_layout import StorageLayout


def test_public_exam_hides_authoring_data() -> None:
    exam = _exam()
    exam.instructions = [
        "Time limit: 90 minutes. Total: 100 points.",
        "Answer indices are zero-based.",
        "Show your reasoning for open-ended questions.",
    ]
    public = public_practice_exam(exam)

    payload = public.model_dump(mode="json")
    question = payload["questions"][0]
    assert "answer_index" not in question
    assert "rubric" not in question
    assert "source_ids" not in question
    assert "ppi_pattern_ids" not in question
    assert payload["questions"][0]["prompt"] == "Question 1?"
    assert len(payload["questions"]) == 20
    assert public.instructions == ["Show your reasoning for open-ended questions."]


def test_generation_input_has_bounded_defaults_and_unique_sources() -> None:
    request = PracticeExamGenerationInput()

    assert request.question_count == 25
    assert request.duration_minutes == 90
    with pytest.raises(ValueError, match="duplicate"):
        PracticeExamGenerationInput(ppi_source_ids=["ppi-42", "ppi-42"])
    with pytest.raises(ValueError):
        PracticeExamGenerationInput(question_count=19)


def test_store_isolates_users_and_lists_newest_first(tmp_path: Path) -> None:
    store = PracticeExamStore(StorageLayout(tmp_path))
    older = _exam(exam_id="a" * 32)
    newer = _exam(exam_id="b" * 32, created_at=older.created_at + timedelta(minutes=1))

    store.write(user_id="student-a", course_id="ml", exam=older)
    store.write(user_id="student-a", course_id="ml", exam=newer)

    assert store.read(user_id="student-a", course_id="ml", exam_id=older.id) == older
    assert [item.id for item in store.list(user_id="student-a", course_id="ml")] == [
        newer.id,
        older.id,
    ]
    with pytest.raises(FileNotFoundError):
        store.read(user_id="student-b", course_id="ml", exam_id=older.id)


def test_store_keeps_exams_immutable_and_deletes_exact_exam(tmp_path: Path) -> None:
    store = PracticeExamStore(StorageLayout(tmp_path))
    exam = _exam()
    store.write(user_id="student-a", course_id="ml", exam=exam)

    with pytest.raises(FileExistsError):
        store.write(user_id="student-a", course_id="ml", exam=exam)
    assert store.delete(user_id="student-a", course_id="ml", exam_id=exam.id) is True
    assert store.delete(user_id="student-a", course_id="ml", exam_id=exam.id) is False


def _exam(
    *,
    exam_id: str = "e" * 32,
    created_at: datetime | None = None,
) -> PracticeExam:
    questions = [
        PracticeExamQuestion(
            id=f"question-{index:02d}",
            kind="multiple_choice" if index % 2 else "open_ended",
            prompt=f"Question {index}?",
            points=2,
            difficulty="standard",
            options=["First", "Second"] if index % 2 else [],
            answer_index=1 if index % 2 else None,
            rubric=[] if index % 2 else ["Uses invariance."],
            source_ids=[f"lecture-{index:02d}:section"],
            ppi_pattern_ids=["ppi-42"] if index == 1 else [],
        )
        for index in range(1, 21)
    ]
    return PracticeExam(
        id=exam_id,
        course_id="ml",
        title="Machine Learning practice exam",
        language="en",
        instructions=["Answer every question."],
        duration_minutes=90,
        created_at=created_at or datetime(2026, 7, 31, 8, 0, tzinfo=UTC),
        total_points=40,
        source_revision="f" * 64,
        source_ids=[question.source_ids[0] for question in questions],
        ppi_source_ids=["ppi-42"],
        questions=questions,
    )
