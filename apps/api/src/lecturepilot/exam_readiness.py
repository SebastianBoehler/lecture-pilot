from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from lecturepilot.assessment_prompts import readiness_prompt
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_content_filter import is_learning_section
from lecturepilot.models import Lecture
from lecturepilot.learning_map_models import LearningMap, LearningMapGate

MAX_EXAM_QUESTIONS = 10
PASSING_SCORE = 0.7
MAX_MULTIPLE_CHOICE_QUESTIONS = 6


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
    source_excerpt: str = Field(default="", max_length=6000)
    source_ref: str | None = None


class ExamReadinessCheck(BaseModel):
    course_id: str
    passing_score: float = PASSING_SCORE
    published_lecture_count: int
    coverage: list[ExamReadinessCoverage]
    questions: list[ExamReadinessQuestion]


class ExamReadinessPublicQuestion(BaseModel):
    id: str
    kind: Literal["multiple_choice", "open_ended"]
    lecture_id: str
    lecture_title: str
    section_id: str
    section_title: str
    prompt: str
    options: list[str] = Field(default_factory=list)
    source_ref: str | None = None


class ExamReadinessPublicCheck(BaseModel):
    course_id: str
    passing_score: float = PASSING_SCORE
    published_lecture_count: int
    coverage: list[ExamReadinessCoverage]
    questions: list[ExamReadinessPublicQuestion]


def public_exam_readiness_check(check: ExamReadinessCheck) -> ExamReadinessPublicCheck:
    return ExamReadinessPublicCheck(
        course_id=check.course_id,
        passing_score=check.passing_score,
        published_lecture_count=check.published_lecture_count,
        coverage=check.coverage,
        questions=[
            ExamReadinessPublicQuestion.model_validate(
                question.model_dump(exclude={"answer_index", "rubric", "source_excerpt"})
            )
            for question in check.questions
        ],
    )


def build_exam_readiness_check(
    *,
    course_id: str,
    documents: list[CanvasDocument],
    lectures: list[Lecture],
    learning_maps: list[LearningMap],
) -> ExamReadinessCheck:
    lecture_titles = {lecture.id: lecture.title for lecture in lectures}
    maps = {item.lecture_id: item for item in learning_maps if item.course_id == course_id}
    if any(document.lecture_id not in maps for document in documents):
        raise ValueError("Readiness requires a published learning map for every lecture.")
    by_lecture = [
        _questions_for_document(
            document,
            lecture_titles.get(document.lecture_id, document.title),
            maps[document.lecture_id],
        )
        for document in documents
    ]
    question_limit = max(MAX_EXAM_QUESTIONS, sum(bool(group) for group in by_lecture))
    questions = _mixed_questions(by_lecture, question_limit)
    coverage = [
        ExamReadinessCoverage(
            lecture_id=document.lecture_id,
            lecture_title=lecture_titles.get(document.lecture_id, document.title),
            question_count=sum(
                1 for question in questions if question.lecture_id == document.lecture_id
            ),
        )
        for document in documents
    ]
    return ExamReadinessCheck(
        course_id=course_id,
        published_lecture_count=len(documents),
        coverage=coverage,
        questions=questions,
    )


def _questions_for_document(
    document: CanvasDocument, lecture_title: str, learning_map: LearningMap
) -> list[ExamReadinessQuestion]:
    gates = {gate.id: gate for gate in learning_map.gates}
    multiple_choice = []
    open_ended = []
    for section in document.sections:
        if not is_learning_section(section):
            continue
        for block in section.blocks:
            if question := _quiz_question(document, lecture_title, section, block):
                multiple_choice.append(question)
        for block in section.blocks:
            if question := _open_question(
                document, lecture_title, section, block, gates.get(block.id)
            ):
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
    prompt = readiness_prompt(block.text, "quiz")
    if not prompt:
        return None
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
    block: CanvasBlock,
    gate: LearningMapGate | None,
) -> ExamReadinessQuestion | None:
    if block.type != "checkpoint":
        return None
    prompt = readiness_prompt(block.text, "checkpoint")
    if not prompt:
        return None
    if gate is None or gate.section_id != section.id or gate.prompt != block.text:
        return None
    rubric = [item.description for item in gate.evidence_criteria if item.required]
    if not rubric:
        return None
    return ExamReadinessQuestion(
        id=f"{document.lecture_id}:{block.id}:open",
        kind="open_ended",
        lecture_id=document.lecture_id,
        lecture_title=lecture_title,
        section_id=section.id,
        section_title=section.title,
        prompt=prompt,
        rubric=rubric,
        source_excerpt="\n".join(
            item.text or "\n".join(item.items)
            for item in section.blocks
            if item.type in {"paragraph", "callout", "list", "math", "table"}
        )[:6000],
        source_ref=section.source_ref or document.source_ref,
    )


def _round_robin(
    question_groups: list[list[ExamReadinessQuestion]], limit: int
) -> list[ExamReadinessQuestion]:
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


def _mixed_questions(
    question_groups: list[list[ExamReadinessQuestion]], limit: int
) -> list[ExamReadinessQuestion]:
    groups = [group for group in question_groups if group]
    selected = _coverage_questions(groups, limit)
    remaining = limit - len(selected)
    if remaining <= 0:
        return selected[:limit]
    selected_ids = {question.id for question in selected}
    leftovers = [
        [question for question in questions if question.id not in selected_ids]
        for questions in groups
    ]
    open_leftovers = [
        [question for question in group if question.kind == "open_ended"] for group in leftovers
    ]
    added_open = _round_robin([group for group in open_leftovers if group], remaining)
    selected.extend(added_open)
    remaining = limit - len(selected)
    if remaining <= 0:
        return selected[:limit]
    selected_ids.update(question.id for question in added_open)
    mc_budget = max(
        0,
        MAX_MULTIPLE_CHOICE_QUESTIONS
        - sum(question.kind == "multiple_choice" for question in selected),
    )
    mc_leftovers = [
        [
            question
            for question in group
            if question.id not in selected_ids and question.kind == "multiple_choice"
        ]
        for group in leftovers
    ]
    added_mc = _round_robin(
        [group for group in mc_leftovers if group],
        min(remaining, mc_budget),
    )
    selected.extend(added_mc)
    return selected[:limit]


def _coverage_questions(
    groups: list[list[ExamReadinessQuestion]], limit: int
) -> list[ExamReadinessQuestion]:
    selected = []
    mc_count = 0
    for group in groups[:limit]:
        multiple_choice = next(
            (question for question in group if question.kind == "multiple_choice"),
            None,
        )
        open_ended = next(
            (question for question in group if question.kind == "open_ended"),
            None,
        )
        if multiple_choice is not None and mc_count < MAX_MULTIPLE_CHOICE_QUESTIONS:
            selected.append(multiple_choice)
            mc_count += 1
        elif open_ended is not None:
            selected.append(open_ended)
        elif multiple_choice is not None:
            selected.append(multiple_choice)
            mc_count += 1
    return selected


def _trim(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    return normalized if len(normalized) <= limit else f"{normalized[: limit - 3].rstrip()}..."
