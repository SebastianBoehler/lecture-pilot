from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.durable_files import atomic_write_json, exclusive_file_lock, fsync_directory
from lecturepilot.practice_exam_store import PracticeExamStore


class PracticeAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    selected_index: int | None = Field(default=None, ge=0)
    text: str | None = Field(default=None, max_length=12000)


class PracticeSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    answers: dict[str, PracticeAnswer] = Field(max_length=50)


class PracticeAttempt(PracticeSubmission):
    exam_id: str
    course_id: str
    source_revision: str
    created_at: datetime
    assessment: Literal["ungraded"] = "ungraded"
    assistance: Literal["unknown"] = "unknown"


class PracticeAttemptStore:
    """Private immutable answers; solution-sheet scoring remains a separate self-check."""

    def __init__(self, exams: PracticeExamStore) -> None:
        self.exams = exams

    def save(
        self, *, user_id: str, course_id: str, exam_id: str, submission: PracticeSubmission
    ) -> PracticeAttempt:
        with exclusive_file_lock(self.exams.attempt_lock(user_id, course_id, exam_id)):
            exam = self.exams.read(user_id=user_id, course_id=course_id, exam_id=exam_id)
            questions = {q.id: q for q in exam.questions}
            for question_id, answer in submission.answers.items():
                question = questions.get(question_id)
                if question is None or question.status == "invalid":
                    raise ValueError("Answers must refer to active questions in this exam.")
                if question.kind == "multiple_choice":
                    if answer.text is not None or (
                        answer.selected_index is not None
                        and answer.selected_index >= len(question.options)
                    ):
                        raise ValueError("Invalid multiple-choice answer.")
                elif answer.selected_index is not None:
                    raise ValueError("Open questions require a written answer.")
            root = self.exams.layout.practice_exam_dir(user_id, course_id, exam_id) / "attempts"
            path = root / f"{submission.id}.json"
            if path.exists():
                existing = PracticeAttempt.model_validate_json(path.read_text())
                if existing.answers != submission.answers:
                    raise ValueError("This submission was already saved with different answers.")
                return existing
            attempt = PracticeAttempt(
                **submission.model_dump(),
                exam_id=exam_id,
                course_id=course_id,
                source_revision=exam.source_revision,
                created_at=datetime.now(UTC),
            )
            atomic_write_json(path, attempt.model_dump(mode="json"))
            return attempt

    def list(self, *, user_id: str, course_id: str, exam_id: str) -> list[PracticeAttempt]:
        with exclusive_file_lock(self.exams.attempt_lock(user_id, course_id, exam_id)):
            self.exams.read(user_id=user_id, course_id=course_id, exam_id=exam_id)
            root = self.exams.layout.practice_exam_dir(user_id, course_id, exam_id) / "attempts"
            records = [
                PracticeAttempt.model_validate_json(path.read_text())
                for path in root.glob("*.json")
            ]
            return sorted(records, key=lambda record: record.created_at, reverse=True)

    def delete(self, *, user_id: str, course_id: str, exam_id: str, attempt_id: UUID) -> None:
        with exclusive_file_lock(self.exams.attempt_lock(user_id, course_id, exam_id)):
            self.exams.read(user_id=user_id, course_id=course_id, exam_id=exam_id)
            root = self.exams.layout.practice_exam_dir(user_id, course_id, exam_id) / "attempts"
            path = root / f"{attempt_id}.json"
            path.unlink()
            fsync_directory(root)
