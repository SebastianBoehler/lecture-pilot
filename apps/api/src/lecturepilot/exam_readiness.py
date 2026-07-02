from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.models import Lecture

MAX_EXAM_QUESTIONS = 10
PASSING_SCORE = 0.7


class ExamReadinessCoverage(BaseModel):
    lecture_id: str
    lecture_title: str
    question_count: int = Field(ge=0)


class ExamReadinessQuestion(BaseModel):
    id: str
    kind: Literal["multiple_choice", "open_ended"]
    lecture_id: str
    lecture_title: str
    section_id: str
    section_title: str
    prompt: str
    options: list[str] = Field(default_factory=list)
    answer_index: int | None = Field(default=None, ge=0)
    rubric: list[str] = Field(default_factory=list)
    source_ref: str | None = None


class ExamReadinessCheck(BaseModel):
    course_id: str
    passing_score: float = PASSING_SCORE
    published_lecture_count: int
    coverage: list[ExamReadinessCoverage]
    questions: list[ExamReadinessQuestion]


def build_exam_readiness_check(
    *,
    course_id: str,
    documents: list[CanvasDocument],
    lectures: list[Lecture],
) -> ExamReadinessCheck:
    lecture_titles = {lecture.id: lecture.title for lecture in lectures}
    by_lecture = [_questions_for_document(document, lecture_titles.get(document.lecture_id, document.title)) for document in documents]
    questions = _round_robin([questions for questions in by_lecture if questions], MAX_EXAM_QUESTIONS)
    coverage = [
        ExamReadinessCoverage(
            lecture_id=document.lecture_id,
            lecture_title=lecture_titles.get(document.lecture_id, document.title),
            question_count=sum(1 for question in questions if question.lecture_id == document.lecture_id),
        )
        for document in documents
    ]
    return ExamReadinessCheck(
        course_id=course_id,
        published_lecture_count=len(documents),
        coverage=coverage,
        questions=questions,
    )


def _questions_for_document(document: CanvasDocument, lecture_title: str) -> list[ExamReadinessQuestion]:
    multiple_choice = []
    open_ended = []
    for section in document.sections:
        for block in section.blocks:
            if question := _quiz_question(document, lecture_title, section, block):
                multiple_choice.append(question)
        if question := _open_question(document, lecture_title, section):
            open_ended.append(question)
    return [*multiple_choice[:2], *open_ended[:2]]


def _quiz_question(
    document: CanvasDocument,
    lecture_title: str,
    section: CanvasSection,
    block: CanvasBlock,
) -> ExamReadinessQuestion | None:
    if block.type not in {"quiz", "component"}:
        return None
    if block.answer_index is None or block.answer_index >= len(block.items) or len(block.items) < 2:
        return None
    prompt = _trim(block.text or block.caption or section.title, 500)
    return ExamReadinessQuestion(
        id=f"{document.lecture_id}:{block.id}",
        kind="multiple_choice",
        lecture_id=document.lecture_id,
        lecture_title=lecture_title,
        section_id=section.id,
        section_title=section.title,
        prompt=prompt,
        options=[_trim(item, 180) for item in block.items[:6]],
        answer_index=block.answer_index,
        rubric=[f"Review {section.title} in {lecture_title}."],
        source_ref=section.source_ref or document.source_ref,
    )


def _open_question(
    document: CanvasDocument,
    lecture_title: str,
    section: CanvasSection,
) -> ExamReadinessQuestion | None:
    rubric = _section_rubric(section)
    if not rubric:
        return None
    return ExamReadinessQuestion(
        id=f"{document.lecture_id}:{section.id}:open",
        kind="open_ended",
        lecture_id=document.lecture_id,
        lecture_title=lecture_title,
        section_id=section.id,
        section_title=section.title,
        prompt=(
            f"Explain {section.title} as you would in an exam answer. "
            "Name the key idea, when it applies, and one common mistake."
        ),
        rubric=rubric,
        source_ref=section.source_ref or document.source_ref,
    )


def _section_rubric(section: CanvasSection) -> list[str]:
    rubric = []
    for block in section.blocks:
        if block.type in {"paragraph", "callout", "checkpoint"} and block.text:
            rubric.append(_trim(block.text, 220))
        if block.type == "math" and block.text:
            rubric.append(_trim(block.text, 160))
        if block.type == "list":
            rubric.extend(_trim(item, 140) for item in block.items[:3])
        if len(rubric) >= 3:
            return rubric[:3]
    return rubric[:3]


def _round_robin(question_groups: list[list[ExamReadinessQuestion]], limit: int) -> list[ExamReadinessQuestion]:
    selected = []
    index = 0
    while len(selected) < limit:
        added = False
        for questions in question_groups:
            if index < len(questions):
                selected.append(questions[index])
                added = True
                if len(selected) == limit:
                    break
        if not added:
            break
        index += 1
    return selected


def _trim(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    return normalized if len(normalized) <= limit else f"{normalized[:limit - 3].rstrip()}..."
