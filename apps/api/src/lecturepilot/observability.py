from __future__ import annotations

import hashlib
import importlib
import os
from types import TracebackType
from typing import Any

from lecturepilot.models import AgentTurnInput, AgentTurnResult

_DISABLED = {"", "0", "false", "none", "off"}
_CONTENT_POLICIES = {"metadata", "redacted", "full"}


class ObservabilityConfigurationError(RuntimeError):
    """Raised when an enabled observability backend cannot be configured."""


class NoopSpan:
    def __enter__(self) -> "NoopSpan":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        return False

    def set_outputs(self, value: Any) -> None:
        return None


class Observability:
    enabled = False

    def agent_turn_span(self, turn: AgentTurnInput) -> NoopSpan:
        return NoopSpan()

    def tool_span(self, name: str, **attributes: Any) -> NoopSpan:
        return NoopSpan()

    def model_span(self, **attributes: Any) -> NoopSpan:
        return NoopSpan()

    def result_output(self, result: AgentTurnResult) -> dict[str, Any]:
        return _result_metadata(result)


class MlflowObservability(Observability):
    enabled = True

    def __init__(self, mlflow: Any, *, trace_content: str) -> None:
        self._mlflow = mlflow
        self.trace_content = trace_content

    def agent_turn_span(self, turn: AgentTurnInput) -> "MlflowSpan":
        attributes = {
            "course_id": turn.course_id,
            "lecture_id": turn.lecture_id,
            "attendance": turn.attendance.value,
            "user_key": _hash_text(turn.user_id),
            "trace_content": self.trace_content,
            "message_chars": len(turn.message),
        }
        return self._span(
            "lecturepilot.agent_turn",
            "CHAIN",
            attributes,
            _turn_inputs(turn, self.trace_content),
        )

    def tool_span(self, name: str, **attributes: Any) -> "MlflowSpan":
        return self._span(f"lecturepilot.{name}", "TOOL", _clean_attributes(attributes), None)

    def model_span(self, **attributes: Any) -> "MlflowSpan":
        return self._span("lecturepilot.call_tutor_model", "LLM", _clean_attributes(attributes), None)

    def result_output(self, result: AgentTurnResult) -> dict[str, Any]:
        output = _result_metadata(result)
        if self.trace_content == "full":
            output["message"] = result.message
        elif self.trace_content == "redacted":
            output["message_sha256"] = _hash_text(result.message)
        return output

    def _span(
        self,
        name: str,
        span_type: str,
        attributes: dict[str, Any],
        inputs: dict[str, Any] | None,
    ) -> "MlflowSpan":
        return MlflowSpan(
            self._mlflow.start_span(name=name, span_type=span_type, attributes=attributes),
            inputs=inputs,
        )


class MlflowSpan:
    def __init__(self, context: Any, *, inputs: dict[str, Any] | None) -> None:
        self._context = context
        self._inputs = inputs
        self._span: Any = None

    def __enter__(self) -> "MlflowSpan":
        self._span = self._context.__enter__()
        if self._inputs is not None and hasattr(self._span, "set_inputs"):
            self._span.set_inputs(self._inputs)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        return self._context.__exit__(exc_type, exc, traceback)

    def set_outputs(self, value: Any) -> None:
        if self._span is not None and hasattr(self._span, "set_outputs"):
            self._span.set_outputs(value)


def observability_from_env() -> Observability:
    backend = os.getenv("LECTUREPILOT_OBSERVABILITY", "none").strip().lower()
    if backend in _DISABLED:
        return Observability()
    if backend != "mlflow":
        raise ObservabilityConfigurationError(f"Unsupported observability backend: {backend}")
    mlflow = _import_mlflow()
    if tracking_uri := os.getenv("MLFLOW_TRACKING_URI"):
        mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT", "lecturepilot-dev"))
    return MlflowObservability(mlflow, trace_content=_trace_content())


def _import_mlflow() -> Any:
    try:
        return importlib.import_module("mlflow")
    except ImportError as exc:
        raise ObservabilityConfigurationError(
            "LECTUREPILOT_OBSERVABILITY=mlflow requires `pip install -e apps/api[observability]`."
        ) from exc


def _trace_content() -> str:
    value = os.getenv("LECTUREPILOT_TRACE_CONTENT", "metadata").strip().lower()
    if value not in _CONTENT_POLICIES:
        raise ObservabilityConfigurationError(
            "LECTUREPILOT_TRACE_CONTENT must be metadata, redacted, or full."
        )
    return value


def _turn_inputs(turn: AgentTurnInput, policy: str) -> dict[str, Any]:
    inputs: dict[str, Any] = {
        "course_id": turn.course_id,
        "lecture_id": turn.lecture_id,
        "attendance": turn.attendance.value,
        "message_chars": len(turn.message),
    }
    if policy == "full":
        inputs["message"] = turn.message
    elif policy == "redacted":
        inputs["message_sha256"] = _hash_text(turn.message)
    return inputs


def _result_metadata(result: AgentTurnResult) -> dict[str, Any]:
    return {
        "model": result.model,
        "message_chars": len(result.message),
        "canvas_commands": [command.type for command in result.canvas_commands],
        "quality_gate": result.quality_gate.status.value if result.quality_gate else None,
    }


def _clean_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in attributes.items() if value is not None}


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
