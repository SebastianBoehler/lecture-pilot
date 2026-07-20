from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import json
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from pathlib import Path
from typing import Any, Iterator


LOGGER_NAME = "uvicorn.error.lecturepilot.metadata"
logger = logging.getLogger(LOGGER_NAME)
_request_id: ContextVar[str | None] = ContextVar("lecturepilot_request_id", default=None)
_operation_id: ContextVar[str | None] = ContextVar("lecturepilot_operation_id", default=None)

_SAFE_KEYS = {
    "account_type",
    "applied",
    "asset_extension",
    "attendance",
    "attempt",
    "canvas_commands",
    "course_count",
    "course_id",
    "duration_ms",
    "exception_type",
    "generation_id",
    "latency_ms",
    "lecture_count",
    "lecture_id",
    "message_chars",
    "method",
    "model",
    "ok",
    "operation_id",
    "outcome",
    "preview",
    "provider",
    "quality_gate",
    "reason",
    "request_id",
    "requested_count",
    "root_cause_type",
    "route",
    "section_count",
    "section_id",
    "section_index",
    "source_count",
    "span",
    "span_type",
    "stage",
    "status",
    "status_code",
    "support_profile",
    "tool",
    "trace_content",
    "warning_count",
    "workload",
}


@contextmanager
def request_scope(request_id: str) -> Iterator[None]:
    token = _request_id.set(request_id)
    try:
        yield
    finally:
        _request_id.reset(token)


@contextmanager
def operation_scope(operation_id: str) -> Iterator[None]:
    token = _operation_id.set(operation_id)
    try:
        yield
    finally:
        _operation_id.reset(token)


def current_request_id() -> str | None:
    return _request_id.get()


def current_operation_id() -> str | None:
    return _operation_id.get()


def current_correlation_id() -> str | None:
    return current_operation_id() or current_request_id()


def emit_metadata_event(event: str, *, error: bool = False, **values: Any) -> None:
    payload = {"event": event, **safe_metadata(values)}
    if request_id := current_request_id():
        payload.setdefault("request_id", request_id)
    if operation_id := current_operation_id():
        payload.setdefault("operation_id", operation_id)
    message = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    (logger.error if error else logger.info)(message)


def safe_metadata(values: dict[str, Any], allowed_keys: set[str] | None = None) -> dict[str, Any]:
    keys = _SAFE_KEYS if allowed_keys is None else _SAFE_KEYS & allowed_keys
    return {key: value for key, value in values.items() if key in keys and _is_safe_value(value)}


def configure_metadata_file_logging() -> None:
    configured = os.getenv("LECTUREPILOT_METADATA_LOG_PATH", "").strip()
    if not configured:
        return
    path = Path(configured)
    if not path.is_absolute():
        raise RuntimeError("LECTUREPILOT_METADATA_LOG_PATH must be an absolute path.")
    path.parent.mkdir(parents=True, exist_ok=True)
    resolved = str(path.resolve())
    if any(
        getattr(handler, "lecturepilot_log_path", None) == resolved for handler in logger.handlers
    ):
        return
    handler = TimedRotatingFileHandler(
        resolved,
        when="midnight",
        interval=1,
        backupCount=13,
        encoding="utf-8",
        delay=True,
        utc=True,
    )
    handler.lecturepilot_log_path = resolved  # type: ignore[attr-defined]
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


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
