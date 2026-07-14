from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import json
import logging
from time import perf_counter
from types import TracebackType
from typing import Any, Iterator

from lecturepilot.models import AgentTurnInput
from lecturepilot.observability import Observability


LOGGER_NAME = "uvicorn.error.lecturepilot.observability"
logger = logging.getLogger(LOGGER_NAME)
_operation_id: ContextVar[str | None] = ContextVar("lecturepilot_operation_id", default=None)

_SAFE_ATTRIBUTE_KEYS = {
    "asset_extension",
    "attendance",
    "attempt",
    "course_id",
    "generation_id",
    "lecture_id",
    "message_chars",
    "model",
    "operation_id",
    "preview",
    "provider",
    "section_count",
    "stage",
    "status",
    "support_profile",
    "tool",
    "trace_content",
    "user_key",
    "warning_count",
    "workload",
}
_SAFE_OUTPUT_KEYS = {
    "canvas_commands",
    "message_chars",
    "model",
    "ok",
    "quality_gate",
    "section_count",
    "warning_count",
}


@contextmanager
def operation_scope(operation_id: str) -> Iterator[None]:
    token = _operation_id.set(operation_id)
    try:
        yield
    finally:
        _operation_id.reset(token)


def current_operation_id() -> str | None:
    return _operation_id.get()


class LoggingObservability(Observability):
    """Metadata-only JSON spans emitted through the process logging pipeline."""

    enabled = True
    trace_content = "metadata"

    def agent_turn_span(self, turn: AgentTurnInput) -> "LoggingSpan":
        return LoggingSpan(
            "lecturepilot.agent_turn",
            span_type="CHAIN",
            attributes={
                "course_id": turn.course_id,
                "lecture_id": turn.lecture_id,
                "attendance": turn.attendance.value,
                "trace_content": self.trace_content,
                "message_chars": len(turn.message),
            },
        )

    def tool_span(self, name: str, **attributes: Any) -> "LoggingSpan":
        return LoggingSpan(
            f"lecturepilot.{name}",
            span_type="TOOL",
            attributes=attributes,
        )

    def model_span(self, **attributes: Any) -> "LoggingSpan":
        return LoggingSpan(
            "lecturepilot.call_model",
            span_type="LLM",
            attributes=attributes,
        )


class LoggingSpan:
    def __init__(self, name: str, *, span_type: str, attributes: dict[str, Any]) -> None:
        self.name = name
        self.span_type = span_type
        self.attributes = _safe_metadata(attributes, _SAFE_ATTRIBUTE_KEYS)
        self.outputs: dict[str, Any] = {}
        self.started_at = 0.0

    def __enter__(self) -> "LoggingSpan":
        self.started_at = perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        payload: dict[str, Any] = {
            "event": "observability.span_finished",
            "span": self.name,
            "span_type": self.span_type,
            "status": "error" if exc_type else "ok",
            "latency_ms": round((perf_counter() - self.started_at) * 1000, 3),
            **self.attributes,
            **self.outputs,
        }
        if operation_id := current_operation_id():
            payload.setdefault("operation_id", operation_id)
        if exc_type is not None:
            payload["exception_type"] = exc_type.__name__
        if root_cause_type := _root_cause_type(exc):
            payload["root_cause_type"] = root_cause_type
        message = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        if exc_type is None:
            logger.info(message)
        else:
            logger.error(message)
        return False

    def set_outputs(self, value: Any) -> None:
        if isinstance(value, dict):
            self.outputs = _safe_metadata(value, _SAFE_OUTPUT_KEYS)


def _safe_metadata(values: dict[str, Any], allowed_keys: set[str]) -> dict[str, Any]:
    return {
        key: value for key, value in values.items() if key in allowed_keys and _is_safe_value(value)
    }


def _is_safe_value(value: Any) -> bool:
    if value is None or isinstance(value, (bool, int, float)):
        return True
    if isinstance(value, str):
        return len(value) <= 200
    return (
        isinstance(value, list)
        and len(value) <= 20
        and all(
            item is None
            or isinstance(item, (bool, int, float))
            or (isinstance(item, str) and len(item) <= 200)
            for item in value
        )
    )


def _root_cause_type(exc: BaseException | None) -> str | None:
    if exc is None:
        return None
    current = exc
    seen = {id(exc)}
    while True:
        next_error = current.__cause__
        if next_error is None and not current.__suppress_context__:
            next_error = current.__context__
        if next_error is None or id(next_error) in seen:
            break
        current = next_error
        seen.add(id(current))
    return type(current).__name__ if current is not exc else None
