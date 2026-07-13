from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import logging
from typing import Any
from uuid import UUID

from lecturepilot.database import Database
from lecturepilot.db_models import ModelUsageEventRecord


logger = logging.getLogger(__name__)


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
        response = await completion(**kwargs)
        self.record_response(response, model=str(kwargs.get("model") or "unknown"))
        return response

    def record_response(self, response: Any, *, model: str) -> None:
        scope = _scope.get()
        if scope is None or not self.database.configured:
            return
        try:
            actor_user_id = UUID(scope.actor_user_id)
            course_id = UUID(scope.course_id)
        except ValueError:
            return
        tokens = usage_tokens_from_response(response)
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
    if recorder is None:
        return await completion(**kwargs)
    return await recorder.complete(completion, **kwargs)


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
