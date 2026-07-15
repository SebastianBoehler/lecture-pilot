from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from pathlib import Path
import re
import secrets
import time


LOGGER_NAME = "lecturepilot_latex_compiler.requests"
_LOGGER = logging.getLogger(LOGGER_NAME)
_SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


def safe_request_id(value: str | None) -> str:
    candidate = (value or "").strip()
    if _SAFE_REQUEST_ID.fullmatch(candidate):
        return candidate
    return secrets.token_hex(16)


@dataclass
class RequestDiagnostics:
    request_id: str
    started: float = field(default_factory=time.monotonic)
    status: int = 500
    code: str = "internal_error"
    exception_type: str | None = None

    def record(self, status: int, code: str) -> None:
        self.status = status
        self.code = code

    def record_exception(self, exception: Exception) -> None:
        self.exception_type = type(exception).__name__[:80]

    def emit(self) -> None:
        payload = {
            "code": self.code,
            "event": "latex_compile_request",
            "latency_ms": max(0, round((time.monotonic() - self.started) * 1000)),
            "request_id": self.request_id,
            "status": self.status,
        }
        if self.exception_type is not None:
            payload["exception_type"] = self.exception_type
        _LOGGER.info(json.dumps(payload, separators=(",", ":"), sort_keys=True))


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    configured = os.getenv("LECTUREPILOT_METADATA_LOG_PATH", "").strip()
    if not configured:
        return
    path = Path(configured)
    if not path.is_absolute():
        raise RuntimeError("LECTUREPILOT_METADATA_LOG_PATH must be an absolute path.")
    path.parent.mkdir(parents=True, exist_ok=True)
    resolved = str(path.resolve())
    if any(
        getattr(handler, "lecturepilot_log_path", None) == resolved
        for handler in _LOGGER.handlers
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
    _LOGGER.addHandler(handler)
    _LOGGER.setLevel(logging.INFO)
    _LOGGER.propagate = False
