from __future__ import annotations

from time import perf_counter
from types import TracebackType
from typing import Any

from lecturepilot.metadata_events import (
    LOGGER_NAME,
    current_operation_id,
    emit_metadata_event,
    logger,
    operation_scope,
    safe_metadata,
)
from lecturepilot.models import AgentTurnInput
from lecturepilot.observability import Observability


__all__ = ["LOGGER_NAME", "current_operation_id", "logger", "operation_scope"]

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
    "requested_count",
    "section_count",
    "section_id",
    "section_index",
    "source_count",
    "stage",
    "support_profile",
    "tool",
    "trace_content",
    "user_key",
    "warning_count",
    "workload",
}
_SAFE_OUTPUT_KEYS = {
    "account_type",
    "applied",
    "canvas_commands",
    "course_count",
    "duration_ms",
    "lecture_count",
    "message_chars",
    "model",
    "ok",
    "outcome",
    "quality_gate",
    "reason",
    "section_count",
    "source_count",
    "warning_count",
}


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
        self.attributes = safe_metadata(attributes, _SAFE_ATTRIBUTE_KEYS)
        self.outputs: dict[str, Any] = {}
        self.started_at = 0.0

    def __enter__(self) -> "LoggingSpan":
        self.started_at = perf_counter()
        emit_metadata_event(
            "observability.span_started",
            span=self.name,
            span_type=self.span_type,
            status="started",
            **self.attributes,
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        payload: dict[str, Any] = {
            "span": self.name,
            "span_type": self.span_type,
            "latency_ms": round((perf_counter() - self.started_at) * 1000, 3),
            **self.attributes,
            **self.outputs,
            "status": "error" if exc_type else "ok",
        }
        if exc_type is not None:
            payload["exception_type"] = exc_type.__name__
        if root_cause_type := _root_cause_type(exc):
            payload["root_cause_type"] = root_cause_type
        emit_metadata_event(
            "observability.span_finished",
            error=exc_type is not None,
            **payload,
        )
        return False

    def set_outputs(self, value: Any) -> None:
        if isinstance(value, dict):
            self.outputs = safe_metadata(value, _SAFE_OUTPUT_KEYS)


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
