from __future__ import annotations

import re

from lecturepilot.practice_exam_models import PracticeExam
from lecturepilot.practice_exam_options import has_equivalent_numeric_options


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
        if question.status != "active":
            raise PracticeExamValidationError(f"Generated question {question.id} must be active.")
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
            _reject_equivalent_options(question.id, question.options)
            options = [_normalized(option) for option in question.options]
            if any(not option for option in options) or len(options) != len(set(options)):
                raise PracticeExamValidationError(
                    f"Question {question.id} requires distinct non-empty options."
                )
        else:
            if any(not item.strip() for item in question.rubric):
                raise PracticeExamValidationError(
                    f"Question {question.id} requires non-empty rubric criteria."
                )
            if not question.reference_answer or not question.reference_answer.strip():
                raise PracticeExamValidationError(
                    f"Question {question.id} requires a full-credit reference answer."
                )
    used_sources = {source_id for question in exam.questions for source_id in question.source_ids}
    available_lectures = {_lecture_id(source_id) for source_id in authoritative_source_ids}
    cited_lectures = {_lecture_id(source_id) for source_id in used_sources}
    if len(available_lectures) <= question_count and not available_lectures.issubset(
        cited_lectures
    ):
        missing = ", ".join(sorted(available_lectures - cited_lectures))
        raise PracticeExamValidationError(
            f"Practice exam questions must cover every available lecture; missing: {missing}."
        )
    if set(exam.source_ids) != used_sources:
        raise PracticeExamValidationError(
            "Practice exam source ids must exactly match the cited course sources."
        )
    if set(exam.ppi_source_ids) != selected_ppi:
        raise PracticeExamValidationError(
            "Practice exam PPI source ids must match the selected retained sources."
        )
    _reject_protocol_copy(exam, ppi_texts or [])


def validate_practice_exam_review(
    payload: dict,
    *,
    exam: PracticeExam,
    authoritative_source_ids: set[str],
    course_evidence: str,
) -> None:
    reviews = payload.get("reviews")
    if not isinstance(reviews, list):
        raise PracticeExamValidationError("Independent exam review is missing reviews.")
    reviewed_ids = [item.get("question_id") for item in reviews if isinstance(item, dict)]
    expected_ids = [question.id for question in exam.questions]
    if (
        len(reviewed_ids) != len(reviews)
        or len(reviewed_ids) != len(set(reviewed_ids))
        or set(reviewed_ids) != set(expected_ids)
    ):
        raise PracticeExamValidationError("Independent exam review must cover every question once.")
    for item in reviews:
        sources = set(item.get("source_ids") or [])
        if not sources or not sources.issubset(authoritative_source_ids):
            raise PracticeExamValidationError(
                f"Independent exam review cited invalid sources for {item.get('question_id')}."
            )
        if item.get("verdict") != "pass":
            issue = str(item.get("issue") or "answer correctness could not be verified").strip()
            raise PracticeExamValidationError(
                f"Independent answer review rejected {item.get('question_id')}: {issue}"
            )
        question = next(q for q in exam.questions if q.id == item["question_id"])
        _validate_review_support(item, question, course_evidence, authoritative_source_ids)


def _validate_review_support(item, question, course_evidence: str, source_ids: set[str]) -> None:
    prefix = f"Independent answer review rejected {question.id}: "
    if question.kind == "multiple_choice":
        _reject_equivalent_options(question.id, question.options)
    if str(item.get("issue") or "").strip():
        raise PracticeExamValidationError(prefix + "contradictory pass with an unresolved issue")
    if not isinstance(item.get("reasoning"), str) or not item["reasoning"].strip():
        raise PracticeExamValidationError(prefix + "missing solution reasoning")
    if "solved_answer_index" not in item or item["solved_answer_index"] != question.answer_index:
        raise PracticeExamValidationError(prefix + "independently solved answer disagrees with key")
    if question.kind == "multiple_choice" and type(item["solved_answer_index"]) is not int:
        raise PracticeExamValidationError(prefix + "invalid independently solved answer")
    quotations = item.get("evidence_quotes")
    if not isinstance(quotations, list) or not quotations:
        raise PracticeExamValidationError(prefix + "missing source quotation")
    markers = list(
        re.finditer(
            r"(?m)^\[(" + "|".join(re.escape(s) for s in sorted(source_ids)) + r")\] ",
            course_evidence,
        )
    )
    passages = {
        marker.group(1): course_evidence[
            marker.end() : markers[i + 1].start() if i + 1 < len(markers) else len(course_evidence)
        ]
        for i, marker in enumerate(markers)
    }
    quoted_ids = set()
    for quotation in quotations:
        if not isinstance(quotation, dict):
            raise PracticeExamValidationError(prefix + "invalid source quotation")
        source_id, quote = quotation.get("source_id"), quotation.get("quote")
        if (
            source_id not in question.source_ids
            or source_id not in item["source_ids"]
            or not isinstance(quote, str)
            or not quote.strip()
            or _normalized(quote) not in _normalized(passages.get(source_id, ""))
        ):
            raise PracticeExamValidationError(prefix + "unverified source quotation")
        quoted_ids.add(source_id)
    if quoted_ids != set(item["source_ids"]):
        raise PracticeExamValidationError(
            prefix + "every reviewed source needs a verified quotation"
        )


def _reject_equivalent_options(question_id: str, options: list[str]) -> None:
    if has_equivalent_numeric_options(options):
        raise PracticeExamValidationError(
            f"Question {question_id} has numerically equivalent options."
        )


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


def _lecture_id(source_id: str) -> str:
    return source_id.split(":", 1)[0]
