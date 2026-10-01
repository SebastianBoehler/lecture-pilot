"""Score fixed, human-labelled review cases separately from generated-exam diagnostics."""

from __future__ import annotations

from time import perf_counter

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.models import ProviderCapability
from lecturepilot.practice_exam_models import PracticeExam
from lecturepilot.practice_exam_planner import (
    PracticeExamPlanner,
    _exam_review_token_budget,
)
from lecturepilot.practice_exam_prompt import (
    authoritative_canvas_evidence,
    practice_exam_review_messages,
)
from lecturepilot.practice_exam_schema import practice_exam_review_response_format
from lecturepilot.practice_exam_validation import (
    PracticeExamValidationError,
    validate_practice_exam_review,
)
from lecturepilot.providers import ProviderRegistry
from practice_exam_benchmark_client import BenchmarkExamClient


def score_reviews(
    payload: dict, exam: PracticeExam, evidence: str, ids: set[str], gold: dict
) -> dict:
    reviews = payload.get("reviews", [])
    rows = []
    for question in exam.questions:
        matches = [
            item
            for item in reviews
            if isinstance(item, dict) and item.get("question_id") == question.id
        ]
        expected = gold[question.id]
        contract_error = None
        accepted = False
        if len(matches) != 1:
            contract_error = "Missing or duplicate review."
        elif matches[0].get("verdict") == "pass":
            try:
                single = exam.model_copy(update={"questions": [question]})
                validate_practice_exam_review(
                    {"reviews": matches},
                    exam=single,
                    authoritative_source_ids=ids,
                    course_evidence=evidence,
                )
                accepted = True
            except PracticeExamValidationError as exc:
                contract_error = str(exc)
        elif matches[0].get("verdict") != "fail":
            contract_error = "Invalid verdict."
        rows.append(
            {
                "question_id": question.id,
                "category": expected["category"],
                "expected_valid": expected["valid"],
                "accepted": accepted,
                "review_verdict": matches[0].get("verdict")
                if len(matches) == 1
                else None,
                "contract_error": contract_error,
            }
        )
    valid = sum(row["expected_valid"] for row in rows)
    invalid = len(rows) - valid
    return {
        "total": len(rows),
        "valid": valid,
        "invalid": invalid,
        "false_accepts": sum(
            row["accepted"] and not row["expected_valid"] for row in rows
        ),
        "false_rejections": sum(
            not row["accepted"] and row["expected_valid"] for row in rows
        ),
        "contract_errors": sum(row["contract_error"] is not None for row in rows),
        "rows": rows,
    }


async def benchmark_model(
    model: str, fixture: dict, client: BenchmarkExamClient, *, generate: bool
) -> dict:
    registry = ProviderRegistry.from_env(model)
    settings = registry.require_ready(
        [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
    )
    documents = [CanvasDocument.model_validate(item) for item in fixture["documents"]]
    evidence, ids = authoritative_canvas_evidence(documents)
    exam = PracticeExam.model_validate(fixture["candidate"])
    if set(fixture["gold"]) != {question.id for question in exam.questions}:
        raise ValueError("Gold labels must cover the fixed candidate exactly.")
    result = {"model": model, "source_metadata": fixture.get("source_metadata", [])}
    start = perf_counter()
    call_start = len(client.meter.calls)
    try:
        review = await client.complete_exam(
            settings=settings,
            messages=practice_exam_review_messages(course_evidence=evidence, exam=exam),
            response_format=practice_exam_review_response_format(
                question_ids=[q.id for q in exam.questions],
                authoritative_source_ids=ids,
            ),
            max_tokens=_exam_review_token_budget(len(exam.questions)),
        )
        result["fixed_review"] = score_reviews(
            review, exam, evidence, ids, fixture["gold"]
        )
    except Exception as exc:
        result["fixed_review_error"] = {"type": type(exc).__name__, "message": str(exc)}
    result["fixed_review_seconds"] = round(perf_counter() - start, 3)
    result["fixed_review_usage"] = client.meter.calls[call_start:]
    if generate:
        start = perf_counter()
        call_start = len(client.meter.calls)
        try:
            generated = await PracticeExamPlanner(
                provider_registry=registry, model_client=client
            ).plan(
                course_id=exam.course_id,
                course_title=fixture["course_title"],
                language=exam.language,
                duration_minutes=exam.duration_minutes,
                question_count=len(exam.questions),
                documents=documents,
                ppi_sources=fixture.get("ppi_sources", {}),
            )
            result["generated_exam"] = generated.model_dump(mode="json")
            result["generation_status"] = "accepted_by_production_validator"
        except Exception as exc:
            result["generation_status"] = "rejected_or_provider_error"
            result["generation_error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
        result["generation_seconds"] = round(perf_counter() - start, 3)
        result["generation_usage"] = client.meter.calls[call_start:]
    result["provider_outputs"] = client.outputs
    return result
