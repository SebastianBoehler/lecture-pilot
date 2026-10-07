"""Quota and usage ownership for student-triggered readiness grading."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException

from lecturepilot.exam_answer_evaluation import (
    OpenAnswerEvaluation,
    OpenAnswerEvaluationInput,
    _evaluation_messages,
    open_answer_evaluation_response_format,
)
from lecturepilot.authoring_limits import authoring_budget
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_usage import model_usage_scope
from lecturepilot.model_usage_total import model_usage_total
from lecturepilot.usage_quota import UsageQuotaExceeded


async def evaluate_readiness_answers(
    app: FastAPI, *, user_id: str, course_id: str, items: list[OpenAnswerEvaluationInput]
) -> list[OpenAnswerEvaluation]:
    if not items:
        return []
    identity = {
        "tenant_id": app.state.course_tenant_id,
        "user_id": user_id,
        "course_id": course_id,
        "usage_date": datetime.now(UTC).date(),
    }
    input_limit, output_limit = readiness_token_reservation(items)
    reservation = input_limit + output_limit
    try:
        reserved = await asyncio.to_thread(
            app.state.usage_quota.reserve_turn, **identity, reserved_tokens=reservation
        )
    except (UsageQuotaExceeded, ValueError) as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    with model_usage_total() as total:
        try:
            with (
                authoring_budget(
                    request_limit=6 * len(items),
                    input_tokens_limit=input_limit,
                    output_tokens_limit=output_limit,
                ),
                model_usage_scope(
                    actor_user_id=user_id, course_id=course_id, workload="readiness_evaluation"
                ),
            ):
                async with asyncio.timeout(180):
                    return await app.state.open_answer_evaluator.evaluate(items=items)
        except TimeoutError as exc:
            raise ModelExecutionError("Readiness grading exceeded its request deadline.") from exc
        finally:
            if reserved:
                await asyncio.to_thread(
                    app.state.usage_quota.release_turn,
                    **identity,
                    actual_tokens=total.total_tokens,
                    reserved_tokens=reservation,
                )


def readiness_token_reservation(items):
    # Three native-schema attempts, each with two metered transport attempts.
    # UTF-8 byte counts conservatively bound prompt tokens; add message/schema framing
    # and earlier 2000-token candidate outputs retained in native repair history.
    schema_bytes = len(json.dumps(open_answer_evaluation_response_format()).encode("utf-8"))
    prompt_bytes = sum(
        sum(len(message["content"].encode("utf-8")) for message in _evaluation_messages([item]))
        + schema_bytes
        + 2048
        for item in items
    )
    return 6 * prompt_bytes + 12_000 * len(items), 12_000 * len(items)
