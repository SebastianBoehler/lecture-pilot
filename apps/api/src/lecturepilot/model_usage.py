from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import logging
from typing import Any
from uuid import UUID, uuid4

from lecturepilot.database import Database
from lecturepilot.db_models import ModelUsageEventRecord
from lecturepilot.logging_observability import current_operation_id
from lecturepilot.model_request_options import MODEL_REQUEST_TIMEOUT_SECONDS


logger = logging.getLogger(__name__)
MODEL_REQUEST_MAX_ATTEMPTS = 2
MODEL_REQUEST_RETRY_DELAY_SECONDS = 0.5


@dataclass(frozen=True)
class ModelUsageScope:
    actor_user_id: str
    course_id: str
    workload: str


_scope: ContextVar[ModelUsageScope | None] = ContextVar("lecturepilot_model_usage", default=None)


@contextmanager
def model_usage_scope(*, actor_user_id: str, course_id: str, workload: str) -> Iterator[None]:
    token = _scope.set(ModelUsageScope(actor_user_id, course_id, workload))
    try:
        yield
    finally:
        _scope.reset(token)


class ModelUsageRecorder:
    def __init__(self, database: Database, *, tenant_id: str) -> None:
        self.database = database
        self.tenant_id = tenant_id

    async def complete(
        self,
        completion: Callable[..., Awaitable[Any]],
        **kwargs: Any,
    ) -> Any:
        return await _complete_with_attempts(self, completion, kwargs)

    def record_response(
        self,
        response: Any,
        *,
        model: str,
        request_id: str | None = None,
        attempt: int = 1,
    ) -> None:
        self._record(
            model=model,
            request_id=request_id or uuid4().hex,
            attempt=attempt,
            status="succeeded",
            tokens=usage_tokens_from_response(response),
        )

    def record_failure(self, *, model: str, request_id: str, attempt: int, error_type: str) -> None:
        self._record(
            model=model,
            request_id=request_id,
            attempt=attempt,
            status="failed",
            error_type=error_type,
            tokens=_empty_tokens(),
        )

    def _record(
        self,
        *,
        model: str,
        request_id: str,
        attempt: int,
        status: str,
        tokens: dict[str, int],
        error_type: str | None = None,
    ) -> None:
        scope = _scope.get()
        if scope is None or not self.database.configured:
            return
        try:
            actor_user_id = UUID(scope.actor_user_id)
            course_id = UUID(scope.course_id)
        except ValueError:
            return
        provider = model.split("/", 1)[0].lower() if "/" in model else "unknown"
        try:
            with self.database.session() as session:
                session.add(
                    ModelUsageEventRecord(
                        tenant_id=self.tenant_id,
                        course_id=course_id,
                        actor_user_id=actor_user_id,
                        workload=scope.workload,
                        provider=provider,
                        model=model,
                        request_id=request_id,
                        operation_id=current_operation_id(),
                        attempt=attempt,
                        status=status,
                        error_type=error_type,
                        **tokens,
                    )
                )
        except Exception:  # noqa: BLE001 - telemetry must not repeat a paid provider request.
            logger.exception("Model usage recording failed")


async def complete_with_usage(
    recorder: ModelUsageRecorder | None,
    completion: Callable[..., Awaitable[Any]],
    **kwargs: Any,
) -> Any:
    return await _complete_with_attempts(recorder, completion, kwargs)


async def _complete_with_attempts(
    recorder: ModelUsageRecorder | None,
    completion: Callable[..., Awaitable[Any]],
    kwargs: dict[str, Any],
) -> Any:
    request_id = uuid4().hex
    model = str(kwargs.get("model") or "unknown")
    for attempt in range(1, MODEL_REQUEST_MAX_ATTEMPTS + 1):
        try:
            async with asyncio.timeout(MODEL_REQUEST_TIMEOUT_SECONDS + 5):
                response = await completion(**kwargs)
        except Exception as exc:
            if recorder is not None:
                recorder.record_failure(
                    model=model,
                    request_id=request_id,
                    attempt=attempt,
                    error_type=type(exc).__name__[:80],
                )
            if attempt >= MODEL_REQUEST_MAX_ATTEMPTS or not _is_retryable(exc):
                raise
            await asyncio.sleep(MODEL_REQUEST_RETRY_DELAY_SECONDS)
            continue
        if recorder is not None:
            recorder.record_response(
                response,
                model=model,
                request_id=request_id,
                attempt=attempt,
            )
        return response
    raise RuntimeError("Model request attempts were exhausted.")


def usage_tokens_from_response(response: Any) -> dict[str, int]:
    usage = _value(response, "usage")
    prompt_details = _value(usage, "prompt_tokens_details")
    completion_details = _value(usage, "completion_tokens_details")
    input_tokens = _nonnegative(_value(usage, "prompt_tokens"))
    output_tokens = _nonnegative(_value(usage, "completion_tokens"))
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": _nonnegative(_value(usage, "total_tokens")) or input_tokens + output_tokens,
        "cached_input_tokens": _nonnegative(_value(prompt_details, "cached_tokens")),
        "reasoning_tokens": _nonnegative(_value(completion_details, "reasoning_tokens")),
    }


def _empty_tokens() -> dict[str, int]:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cached_input_tokens": 0,
        "reasoning_tokens": 0,
    }


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    status_code = getattr(exc, "status_code", None)
    if status_code in {408, 409, 429, 500, 502, 503, 504}:
        return True
    name = type(exc).__name__.lower()
    return any(
        marker in name
        for marker in (
            "timeout",
            "ratelimit",
            "serviceunavailable",
            "apiconnection",
            "internalserver",
        )
    )


def _value(value: Any, name: str) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _nonnegative(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0
