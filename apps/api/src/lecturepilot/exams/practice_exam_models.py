from __future__ import annotations

from datetime import datetime
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


PracticeExamQuestionKind = Literal["multiple_choice", "multiple_select", "open_ended"]
PracticeExamChoiceFormat = Literal["single_answer", "multiple_answers"]
PracticeExamDifficulty = Literal["introductory", "standard", "advanced"]
PracticeExamQuestionStatus = Literal["active", "invalid"]
MIN_PRACTICE_EXAM_QUESTIONS = 20
MAX_PRACTICE_EXAM_QUESTIONS = 50
MULTIPLE_SELECT_POINTS = 4
_ADMIN_INSTRUCTION = re.compile(
    r"\b(?:time\s*limit|duration|minutes?|total|answer(?:_|\s|-)?ind(?:ex|ices)|"
    r"zero(?:\s|-)?based|zeitlimit|dauer|minuten?|gesamt|antwortind(?:ex|izes)|"
    r"nullbasiert|scoring|penalties|deductions|punktabzug|wertung)\b|\b\d+\s*(?:points?|punkte?)\b",
    re.IGNORECASE,
)


class PracticeExamQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=120)
    kind: PracticeExamQuestionKind
    status: PracticeExamQuestionStatus = "active"
    prompt: str = Field(min_length=1, max_length=2_000)
    points: int = Field(ge=0, le=50)
    difficulty: PracticeExamDifficulty
    options: list[str] = Field(default_factory=list, max_length=6)
    answer_index: int | None = Field(default=None, ge=0, le=5)
    answer_indices: list[Annotated[int, Field(strict=True, ge=0, le=3)]] = Field(
        default_factory=list, max_length=4
    )
    rubric: list[str] = Field(default_factory=list, max_length=8)
    reference_answer: str | None = Field(default=None, max_length=4_000)
    source_ids: list[str] = Field(min_length=1, max_length=8)
    ppi_pattern_ids: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_question_shape(self) -> "PracticeExamQuestion":
        if self.status == "invalid":
            if self.points or self.options or self.answer_index is not None or self.answer_indices:
                raise ValueError("Invalid questions must be zero-point placeholders.")
            if self.rubric or self.reference_answer is not None:
                raise ValueError("Invalid questions cannot contain private answer guidance.")
            return self
        if self.points < 1:
            raise ValueError("Active questions must be worth at least one point.")
        if self.kind in {"multiple_choice", "multiple_select"}:
            if len(self.options) < 2:
                raise ValueError("Multiple-choice questions require at least two options.")
            if self.kind == "multiple_choice":
                if (
                    self.answer_index is None
                    or self.answer_index >= len(self.options)
                    or self.answer_indices
                ):
                    raise ValueError("Multiple-choice questions require one valid answer index.")
            elif (
                len(self.options) != 4
                or self.answer_index is not None
                or not self.answer_indices
                or any(type(i) is not int or i < 0 or i >= 4 for i in self.answer_indices)
                or len(set(self.answer_indices)) != len(self.answer_indices)
            ):
                raise ValueError(
                    "Multiple-answer questions require four options, distinct valid keys."
                )
            if self.rubric:
                raise ValueError("Multiple-choice questions cannot contain an open-answer rubric.")
            if self.reference_answer is not None:
                raise ValueError("Multiple-choice questions cannot contain a reference answer.")
        elif (
            self.options or self.answer_index is not None or self.answer_indices or not self.rubric
        ):
            raise ValueError("Open-ended questions require a rubric and cannot contain options.")
        elif self.reference_answer is not None and not self.reference_answer.strip():
            raise ValueError("Open-ended reference answers cannot be blank.")
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
    total_points: int = Field(ge=1, le=2_500)
    source_revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_ids: list[str] = Field(min_length=1, max_length=240)
    ppi_source_ids: list[str] = Field(default_factory=list, max_length=1)
    questions: list[PracticeExamQuestion] = Field(
        min_length=MIN_PRACTICE_EXAM_QUESTIONS,
        max_length=MAX_PRACTICE_EXAM_QUESTIONS,
    )

    @model_validator(mode="after")
    def validate_totals_and_ids(self) -> "PracticeExam":
        if self.total_points != sum(question.points for question in self.questions):
            raise ValueError("Exam total points must equal the question point total.")
        question_ids = [question.id for question in self.questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Practice exam question ids must be unique.")
        return self


class PracticeExamPublicQuestion(BaseModel):
    id: str
    kind: PracticeExamQuestionKind
    status: PracticeExamQuestionStatus = "active"
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


class PracticeExamSolutionQuestion(BaseModel):
    id: str
    kind: PracticeExamQuestionKind
    status: PracticeExamQuestionStatus = "active"
    points: int
    answer_index: int | None = None
    answer_indices: list[int] = Field(default_factory=list)
    reference_answer: str | None = None
    rubric: list[str] = Field(default_factory=list)


class PracticeExamSolutionSheet(BaseModel):
    exam_id: str
    title: str
    total_points: int
    questions: list[PracticeExamSolutionQuestion]


class PracticeExamGenerationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_count: int = Field(
        default=25,
        ge=MIN_PRACTICE_EXAM_QUESTIONS,
        le=MAX_PRACTICE_EXAM_QUESTIONS,
    )
    duration_minutes: int = Field(default=90, ge=30, le=300)
    ppi_source_ids: list[str] = Field(default_factory=list, max_length=1)
    choice_format: PracticeExamChoiceFormat = "single_answer"


def public_practice_exam(exam: PracticeExam) -> PracticeExamPublic:
    instructions = sanitize_practice_exam_instructions(exam.instructions)
    if any(question.kind == "multiple_select" for question in exam.questions):
        instructions.append(multiple_select_scoring_instruction(exam.language))
    return PracticeExamPublic(
        id=exam.id,
        course_id=exam.course_id,
        title=exam.title,
        language=exam.language,
        instructions=instructions,
        duration_minutes=exam.duration_minutes,
        created_at=exam.created_at,
        total_points=sum(question_display_points(q) for q in exam.questions),
        questions=[
            PracticeExamPublicQuestion(
                id=question.id,
                kind=question.kind,
                status=question.status,
                prompt=question.prompt,
                points=question_display_points(question),
                options=question.options,
            )
            for question in exam.questions
        ],
    )


def practice_exam_solution_sheet(exam: PracticeExam) -> PracticeExamSolutionSheet:
    missing = [
        question.id
        for question in exam.questions
        if question.status == "active"
        and question.kind == "open_ended"
        and not question.reference_answer
    ]
    if missing:
        raise ValueError("This practice exam predates full-credit reference answers.")
    return PracticeExamSolutionSheet(
        exam_id=exam.id,
        title=f"{exam.title} — {'Lösungen' if exam.language == 'de' else 'Solutions'}",
        total_points=sum(question_display_points(q) for q in exam.questions),
        questions=[
            PracticeExamSolutionQuestion(
                id=question.id,
                kind=question.kind,
                status=question.status,
                points=question_display_points(question),
                answer_index=question.answer_index,
                answer_indices=question.answer_indices,
                reference_answer=question.reference_answer,
                rubric=question.rubric,
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


def question_display_points(question: PracticeExamQuestion) -> int:
    if question.kind == "multiple_select" and question.status == "active":
        return MULTIPLE_SELECT_POINTS
    return question.points


def multiple_select_scoring_instruction(language: str) -> str:
    return (
        "Wähle alle richtigen Optionen. Übungswertung: 4 Punkte für die vollständig richtige Auswahl, "
        "sonst −1 pro falscher Auswahl und 0 für unvollständige richtige Auswahlen. Negative Punkte sind möglich."
        if language == "de"
        else "Select all correct options. Practice scoring: 4 points for the complete correct set, "
        "otherwise −1 per wrong selection and 0 for incomplete correct sets. Negative scores are possible."
    )
