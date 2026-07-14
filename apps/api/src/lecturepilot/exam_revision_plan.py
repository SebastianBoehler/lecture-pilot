from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from lecturepilot.exam_readiness import ExamReadinessCheck, ExamReadinessQuestion
from lecturepilot.scaffold_policy import TutorScaffoldPolicy, scaffold_policy_for_revision_task
from lecturepilot.storage_layout import safe_id

GuidanceLevel = Literal["challenge", "standard", "scaffolded"]
QuestionStatus = Literal["correct", "incorrect", "needs_rubric_review"]
RevisionTaskKind = Literal["review_wrong_mc", "review_open_answer"]


class ExamReadinessAnswer(BaseModel):
    question_id: str = Field(min_length=1, max_length=220)
    selected_index: int | None = Field(default=None, ge=0, le=25)
    text: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def require_selection_or_text(self) -> "ExamReadinessAnswer":
        has_selection = self.selected_index is not None
        has_text = bool((self.text or "").strip())
        if has_selection == has_text:
            raise ValueError("Answer must contain either selected_index or text.")
        if self.text is not None:
            self.text = self.text.strip()
        return self


class ExamReadinessAttemptInput(BaseModel):
    answers: list[ExamReadinessAnswer] = Field(min_length=1)


class ExamReadinessQuestionResult(BaseModel):
    question_id: str
    kind: Literal["multiple_choice", "open_ended"]
    lecture_id: str
    section_id: str
    answer_kind: Literal["multiple_choice", "open_ended"]
    correct: bool | None
    selected_index: int | None = None
    correct_index: int | None = None
    status: QuestionStatus


class ExamRevisionTask(BaseModel):
    id: str
    question_id: str
    kind: RevisionTaskKind
    status: Literal["open", "completed"] = "open"
    guidance_level: GuidanceLevel
    lecture_id: str
    lecture_title: str
    section_id: str
    section_title: str
    prompt: str
    source_ref: str | None = None
    rubric: list[str] = Field(default_factory=list)
    expected_evidence: str
    next_action: str
    scaffold_policy: TutorScaffoldPolicy | None = None

    @model_validator(mode="after")
    def default_scaffold_policy(self) -> "ExamRevisionTask":
        if self.scaffold_policy is None:
            self.scaffold_policy = scaffold_policy_for_revision_task(
                guidance_level=self.guidance_level,
                task_kind=self.kind,
            )
        return self


class ExamReadinessAttemptResult(BaseModel):
    attempt_id: str | None = None
    created_at: str | None = None
    course_id: str
    passing_score: float
    score: float | None
    guidance_level: GuidanceLevel
    results: list[ExamReadinessQuestionResult]
    tasks: list[ExamRevisionTask]


def build_exam_revision_plan(
    *,
    check: ExamReadinessCheck,
    answers: list[ExamReadinessAnswer],
    previous_attempts: int = 0,
) -> ExamReadinessAttemptResult:
    answers_by_question = _answers_by_question(answers)
    questions_by_id = {question.id: question for question in check.questions}
    unknown_ids = set(answers_by_question) - set(questions_by_id)
    if unknown_ids:
        raise ValueError(f"Unknown answer question id: {sorted(unknown_ids)[0]}")
    for question in check.questions:
        if question.id not in answers_by_question:
            raise ValueError(f"Missing answer for question {question.id}")

    results = [
        _question_result(question, answers_by_question[question.id]) for question in check.questions
    ]
    score = _score(results)
    guidance_level = _guidance_level(score, previous_attempts)
    return ExamReadinessAttemptResult(
        course_id=check.course_id,
        passing_score=check.passing_score,
        score=score,
        guidance_level=guidance_level,
        results=results,
        tasks=[
            _revision_task(question=question, result=result, guidance_level=guidance_level)
            for question, result in zip(check.questions, results, strict=True)
            if result.status != "correct"
        ],
    )


def _answers_by_question(answers: list[ExamReadinessAnswer]) -> dict[str, ExamReadinessAnswer]:
    by_question: dict[str, ExamReadinessAnswer] = {}
    for answer in answers:
        if answer.question_id in by_question:
            raise ValueError(f"Duplicate answer for question {answer.question_id}")
        by_question[answer.question_id] = answer
    return by_question


def _question_result(
    question: ExamReadinessQuestion, answer: ExamReadinessAnswer
) -> ExamReadinessQuestionResult:
    if question.kind == "multiple_choice":
        if answer.selected_index is None:
            raise ValueError(f"Multiple-choice question {question.id} requires selected_index.")
        if answer.selected_index >= len(question.options):
            raise ValueError(f"Selected option does not exist for question {question.id}.")
        correct = answer.selected_index == question.answer_index
        return ExamReadinessQuestionResult(
            question_id=question.id,
            kind=question.kind,
            lecture_id=question.lecture_id,
            section_id=question.section_id,
            answer_kind="multiple_choice",
            correct=correct,
            selected_index=answer.selected_index,
            correct_index=question.answer_index,
            status="correct" if correct else "incorrect",
        )
    if not answer.text:
        raise ValueError(f"Open-ended question {question.id} requires text.")
    return ExamReadinessQuestionResult(
        question_id=question.id,
        kind=question.kind,
        lecture_id=question.lecture_id,
        section_id=question.section_id,
        answer_kind="open_ended",
        correct=None,
        status="needs_rubric_review",
    )


def _score(results: list[ExamReadinessQuestionResult]) -> float | None:
    scored = [result for result in results if result.answer_kind == "multiple_choice"]
    if not scored:
        return None
    correct = sum(1 for result in scored if result.correct is True)
    return round(correct / len(scored), 4)


def _guidance_level(score: float | None, previous_attempts: int) -> GuidanceLevel:
    if score is None:
        return "scaffolded" if previous_attempts >= 2 else "standard"
    if score >= 0.8:
        return "challenge"
    if score < 0.4:
        return "scaffolded"
    if previous_attempts >= 2:
        return "scaffolded"
    return "standard"


def _revision_task(
    *,
    question: ExamReadinessQuestion,
    result: ExamReadinessQuestionResult,
    guidance_level: GuidanceLevel,
) -> ExamRevisionTask:
    kind: RevisionTaskKind = (
        "review_wrong_mc" if result.status == "incorrect" else "review_open_answer"
    )
    return ExamRevisionTask(
        id=f"{safe_id(question.id)}-review",
        question_id=question.id,
        kind=kind,
        guidance_level=guidance_level,
        lecture_id=question.lecture_id,
        lecture_title=question.lecture_title,
        section_id=question.section_id,
        section_title=question.section_title,
        prompt=question.prompt,
        source_ref=question.source_ref,
        rubric=question.rubric,
        expected_evidence=_expected_evidence(question),
        next_action=_next_action(kind, question),
        scaffold_policy=scaffold_policy_for_revision_task(
            guidance_level=guidance_level,
            task_kind=kind,
        ),
    )


def _expected_evidence(question: ExamReadinessQuestion) -> str:
    if question.rubric:
        return question.rubric[0]
    return f"Explain the key idea from {question.section_title} using the course source."


def _next_action(kind: RevisionTaskKind, question: ExamReadinessQuestion) -> str:
    if kind == "review_wrong_mc":
        return (
            f"Review {question.section_title}, then answer a follow-up without seeing the options."
        )
    return f"Compare your answer with the rubric for {question.section_title} and revise the weak point."
