from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import logging
from random import uniform
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

from lecturepilot.database import Database
from lecturepilot.db_models import ModelUsageEventRecord
from lecturepilot.logging_observability import current_operation_id
from lecturepilot.metadata_events import emit_metadata_event
from lecturepilot.model_rate_limits import model_request_slot, observe_provider_response
from lecturepilot.model_provider_errors import is_retryable_provider_error
from lecturepilot.model_request_options import MODEL_REQUEST_TIMEOUT_SECONDS


logger = logging.getLogger(__name__)
MODEL_REQUEST_MAX_ATTEMPTS = 2
MODEL_REQUEST_RETRY_DELAY_SECONDS = 1.0


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
        *,
        usage_stage: str | None = None,
        **kwargs: Any,
    ) -> Any:
        return await _complete_with_attempts(self, completion, kwargs, usage_stage=usage_stage)

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
    *,
    usage_stage: str | None = None,
    **kwargs: Any,
) -> Any:
    return await _complete_with_attempts(
        recorder,
        completion,
        kwargs,
        usage_stage=usage_stage,
    )


async def _complete_with_attempts(
    recorder: ModelUsageRecorder | None,
    completion: Callable[..., Awaitable[Any]],
    kwargs: dict[str, Any],
    *,
    usage_stage: str | None,
) -> Any:
    request_id = uuid4().hex
    model = str(kwargs.get("model") or "unknown")
    timeout_seconds = float(kwargs.get("timeout") or MODEL_REQUEST_TIMEOUT_SECONDS)
    _enable_litellm_response_headers()
    for attempt in range(1, MODEL_REQUEST_MAX_ATTEMPTS + 1):
        started_at = perf_counter()
        provider_started_at: float | None = None
        try:
            async with model_request_slot(model):
                provider_started_at = perf_counter()
                async with asyncio.timeout(timeout_seconds + 5):
                    response = await completion(**kwargs)
        except Exception as exc:
            _emit_request_event(
                model=model,
                stage=usage_stage,
                attempt=attempt,
                started_at=started_at,
                provider_started_at=provider_started_at,
                error_type=type(exc).__name__[:80],
            )
            if recorder is not None:
                recorder.record_failure(
                    model=model,
                    request_id=request_id,
                    attempt=attempt,
                    error_type=type(exc).__name__[:80],
                )
            if attempt >= MODEL_REQUEST_MAX_ATTEMPTS or not is_retryable_provider_error(exc):
                logger.warning(
                    "Model request exhausted attempts model=%s attempts=%s error_type=%s status=%s",
                    model,
                    attempt,
                    type(exc).__name__,
                    getattr(exc, "status_code", None),
                )
                raise
            provider_delay = observe_provider_response(model, exc)
            backoff = MODEL_REQUEST_RETRY_DELAY_SECONDS * (2 ** (attempt - 1))
            await asyncio.sleep(max(backoff, provider_delay) + uniform(0.0, 0.25))
            continue
        observe_provider_response(model, response)
        tokens = usage_tokens_from_response(response)
        _emit_request_event(
            model=model,
            stage=usage_stage,
            attempt=attempt,
            started_at=started_at,
            provider_started_at=provider_started_at,
            tokens=tokens,
        )
        if recorder is not None:
            recorder.record_response(
                response,
                model=model,
                request_id=request_id,
                attempt=attempt,
            )
        return response
    raise RuntimeError("Model request attempts were exhausted.")


def _emit_request_event(
    *,
    model: str,
    stage: str | None,
    attempt: int,
    started_at: float,
    provider_started_at: float | None,
    tokens: dict[str, int] | None = None,
    error_type: str | None = None,
) -> None:
    finished_at = perf_counter()
    provider_started_at = provider_started_at or finished_at
    emit_metadata_event(
        "model.request_finished",
        error=error_type is not None,
        model=model,
        provider=model.split("/", 1)[0].lower() if "/" in model else "unknown",
        stage=stage,
        attempt=attempt,
        status="failed" if error_type else "succeeded",
        exception_type=error_type,
        queue_wait_ms=round((provider_started_at - started_at) * 1000, 3),
        latency_ms=round((finished_at - provider_started_at) * 1000, 3),
        **(tokens or _empty_tokens()),
    )


def _enable_litellm_response_headers() -> None:
    try:
        import litellm
    except ImportError:
        return
    litellm.return_response_headers = True


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
