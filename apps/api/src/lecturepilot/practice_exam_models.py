from __future__ import annotations

from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


PracticeExamQuestionKind = Literal["multiple_choice", "open_ended"]
PracticeExamDifficulty = Literal["introductory", "standard", "advanced"]
_ADMIN_INSTRUCTION = re.compile(
    r"\b(?:time\s*limit|duration|minutes?|total|answer(?:_|\s|-)?ind(?:ex|ices)|"
    r"zero(?:\s|-)?based|zeitlimit|dauer|minuten?|gesamt|antwortind(?:ex|izes)|"
    r"nullbasiert)\b|\b\d+\s*(?:points?|punkte?)\b",
    re.IGNORECASE,
)


class PracticeExamQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=120)
    kind: PracticeExamQuestionKind
    prompt: str = Field(min_length=1, max_length=2_000)
    points: int = Field(ge=1, le=50)
    difficulty: PracticeExamDifficulty
    options: list[str] = Field(default_factory=list, max_length=6)
    answer_index: int | None = Field(default=None, ge=0, le=5)
    rubric: list[str] = Field(default_factory=list, max_length=8)
    source_ids: list[str] = Field(min_length=1, max_length=8)
    ppi_pattern_ids: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_question_shape(self) -> "PracticeExamQuestion":
        if self.kind == "multiple_choice":
            if len(self.options) < 2:
                raise ValueError("Multiple-choice questions require at least two options.")
            if self.answer_index is None or self.answer_index >= len(self.options):
                raise ValueError("Multiple-choice questions require a valid answer index.")
            if self.rubric:
                raise ValueError("Multiple-choice questions cannot contain an open-answer rubric.")
        elif self.options or self.answer_index is not None or not self.rubric:
            raise ValueError("Open-ended questions require a rubric and cannot contain options.")
        return self


class PracticeExam(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    course_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=240)
    language: str = Field(min_length=2, max_length=20)
    instructions: list[str] = Field(min_length=1, max_length=12)
    duration_minutes: int = Field(ge=30, le=300)
    created_at: datetime
    total_points: int = Field(ge=1, le=2_000)
    source_revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_ids: list[str] = Field(min_length=1, max_length=240)
    ppi_source_ids: list[str] = Field(default_factory=list, max_length=8)
    questions: list[PracticeExamQuestion] = Field(min_length=20, max_length=30)

    @model_validator(mode="after")
    def validate_totals_and_ids(self) -> "PracticeExam":
        if self.total_points != sum(question.points for question in self.questions):
            raise ValueError("Exam total points must equal the question point total.")
        question_ids = [question.id for question in self.questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Practice exam question ids must be unique.")
        if len(self.ppi_source_ids) != len(set(self.ppi_source_ids)):
            raise ValueError("Practice exam PPI source ids must be unique.")
        return self


class PracticeExamPublicQuestion(BaseModel):
    id: str
    kind: PracticeExamQuestionKind
    prompt: str
    points: int
    options: list[str] = Field(default_factory=list)


class PracticeExamPublic(BaseModel):
    id: str
    course_id: str
    title: str
    language: str
    instructions: list[str]
    duration_minutes: int
    created_at: datetime
    total_points: int
    questions: list[PracticeExamPublicQuestion]


class PracticeExamGenerationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_count: int = Field(default=25, ge=20, le=30)
    duration_minutes: int = Field(default=90, ge=30, le=300)
    ppi_source_ids: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def require_unique_sources(self) -> "PracticeExamGenerationInput":
        if len(self.ppi_source_ids) != len(set(self.ppi_source_ids)):
            raise ValueError("PPI source ids cannot contain duplicate values.")
        return self


def public_practice_exam(exam: PracticeExam) -> PracticeExamPublic:
    return PracticeExamPublic(
        id=exam.id,
        course_id=exam.course_id,
        title=exam.title,
        language=exam.language,
        instructions=sanitize_practice_exam_instructions(exam.instructions),
        duration_minutes=exam.duration_minutes,
        created_at=exam.created_at,
        total_points=exam.total_points,
        questions=[
            PracticeExamPublicQuestion(
                id=question.id,
                kind=question.kind,
                prompt=question.prompt,
                points=question.points,
                options=question.options,
            )
            for question in exam.questions
        ],
    )


def sanitize_practice_exam_instructions(instructions: list[str]) -> list[str]:
    safe: list[str] = []
    seen: set[str] = set()
    for instruction in instructions:
        normalized = " ".join(instruction.split())
        key = normalized.casefold()
        if not normalized or key in seen or _ADMIN_INSTRUCTION.search(normalized):
            continue
        safe.append(normalized)
        seen.add(key)
    return safe
