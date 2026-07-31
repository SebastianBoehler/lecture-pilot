from __future__ import annotations

import re

from lecturepilot.practice_exam_models import PracticeExam


_COPY_WINDOW = 60


class PracticeExamValidationError(ValueError):
    """Raised when a generated exam violates the authoritative-source contract."""


def validate_practice_exam(
    exam: PracticeExam,
    *,
    authoritative_source_ids: set[str],
    question_count: int,
    selected_ppi_source_ids: set[str] | None = None,
    ppi_texts: list[str] | None = None,
) -> None:
    if len(exam.questions) != question_count:
        raise PracticeExamValidationError(
            f"Practice exam requested {question_count} questions but received {len(exam.questions)}."
        )
    if not authoritative_source_ids:
        raise PracticeExamValidationError("No authoritative course sources are available.")
    prompts = [_normalized(question.prompt) for question in exam.questions]
    if len(prompts) != len(set(prompts)):
        raise PracticeExamValidationError("Practice exam questions must have unique prompts.")
    kinds = {question.kind for question in exam.questions}
    if kinds != {"multiple_choice", "open_ended"}:
        raise PracticeExamValidationError(
            "Practice exams must mix multiple-choice and open-ended questions."
        )
    selected_ppi = selected_ppi_source_ids or set()
    for question in exam.questions:
        course_sources = set(question.source_ids)
        if not course_sources or not course_sources.issubset(authoritative_source_ids):
            raise PracticeExamValidationError(
                f"Question {question.id} must cite at least one known course source."
            )
        if not set(question.ppi_pattern_ids).issubset(selected_ppi):
            raise PracticeExamValidationError(
                f"Question {question.id} cites an unselected PPI source."
            )
        if question.kind == "multiple_choice":
            options = [_normalized(option) for option in question.options]
            if any(not option for option in options) or len(options) != len(set(options)):
                raise PracticeExamValidationError(
                    f"Question {question.id} requires distinct non-empty options."
                )
        elif any(not item.strip() for item in question.rubric):
            raise PracticeExamValidationError(
                f"Question {question.id} requires non-empty rubric criteria."
            )
    used_sources = {source_id for question in exam.questions for source_id in question.source_ids}
    if set(exam.source_ids) != used_sources:
        raise PracticeExamValidationError(
            "Practice exam source ids must exactly match the cited course sources."
        )
    if set(exam.ppi_source_ids) != selected_ppi:
        raise PracticeExamValidationError(
            "Practice exam PPI source ids must match the selected retained sources."
        )
    _reject_protocol_copy(exam, ppi_texts or [])


def _reject_protocol_copy(exam: PracticeExam, protocol_texts: list[str]) -> None:
    candidate = _normalized(
        " ".join(
            value for question in exam.questions for value in [question.prompt, *question.options]
        )
    )
    for protocol in protocol_texts:
        normalized = _normalized(protocol)
        for start in range(0, max(0, len(normalized) - _COPY_WINDOW + 1), 20):
            if normalized[start : start + _COPY_WINDOW] in candidate:
                raise PracticeExamValidationError(
                    "Generated question copies retained PPI text too closely."
                )


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()
