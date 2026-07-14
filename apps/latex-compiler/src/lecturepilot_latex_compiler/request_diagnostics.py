from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
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

    def record(self, status: int, code: str) -> None:
        self.status = status
        self.code = code

    def emit(self) -> None:
        payload = {
            "code": self.code,
            "event": "latex_compile_request",
            "latency_ms": max(0, round((time.monotonic() - self.started) * 1000)),
            "request_id": self.request_id,
            "status": self.status,
        }
        _LOGGER.info(json.dumps(payload, separators=(",", ":"), sort_keys=True))


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
