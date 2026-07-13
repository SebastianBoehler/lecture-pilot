from __future__ import annotations

import hashlib
import json
import logging
import os
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Any, Callable, Iterator
from urllib.parse import urlparse
from uuid import uuid4

from lecturepilot.auth_html_capture import AuthHtmlCapture


AUTH_ATTEMPT_HEADER = "X-Auth-Attempt-Id"
AUTH_DIAGNOSTIC_LOGGER = "lecturepilot.auth_diagnostics"
AUTH_DIAGNOSTIC_PREFIX = "AUTH_DIAGNOSTIC "
_LOGGER = logging.getLogger(AUTH_DIAGNOSTIC_LOGGER)


@dataclass(frozen=True)
class AuthDiagnostics:
    attempt_id: str
    subject_fingerprint: str
    enabled: bool
    attempt_started: float
    html_capture: AuthHtmlCapture | None = None

    @property
    def html_capture_enabled(self) -> bool:
        return self.html_capture is not None

    def started(self, step: str) -> float:
        started = monotonic()
        self._emit(step, "started", started)
        return started

    def succeeded(self, step: str, started: float, **details: Any) -> None:
        self._emit(step, "succeeded", started, details)

    def failed(self, step: str, started: float, error: BaseException) -> None:
        self._emit(step, "failed", started, _error_details(error))

    def response_hook(self, provider: str) -> Callable[..., None]:
        def capture(response: Any, *_args: Any, **_kwargs: Any) -> None:
            if self.html_capture is None:
                return
            started = monotonic()
            try:
                details = self.html_capture.capture_response(provider, response)
            except Exception as exc:
                self.failed("auth.html_capture", started, exc)
            else:
                if details is not None:
                    self.succeeded("auth.html_capture", started, **details)

        return capture

    def _emit(
        self,
        step: str,
        outcome: str,
        step_started: float,
        details: dict[str, Any] | None = None,
    ) -> None:
        if not self.enabled:
            return
        now = monotonic()
        event = {
            "attempt_id": self.attempt_id,
            "elapsed_ms": round((now - self.attempt_started) * 1000),
            "outcome": outcome,
            "step": step,
            "step_duration_ms": round((now - step_started) * 1000),
            "subject_fingerprint": self.subject_fingerprint,
            "timestamp": datetime.now(UTC).isoformat(),
            **_safe_details(details or {}),
        }
        _LOGGER.warning(
            "%s%s",
            AUTH_DIAGNOSTIC_PREFIX,
            json.dumps(event, ensure_ascii=True, separators=(",", ":"), sort_keys=True),
        )


_DISABLED_DIAGNOSTICS = AuthDiagnostics("untracked", "", False, 0.0, None)
_CURRENT: ContextVar[AuthDiagnostics] = ContextVar(
    "lecturepilot_auth_diagnostics",
    default=_DISABLED_DIAGNOSTICS,
)


@contextmanager
def auth_diagnostic_attempt(username: str) -> Iterator[AuthDiagnostics]:
    attempt_id = uuid4().hex
    diagnostics = AuthDiagnostics(
        attempt_id=attempt_id,
        subject_fingerprint=_fingerprint(username.strip().casefold()),
        enabled=_enabled(),
        attempt_started=monotonic(),
        html_capture=AuthHtmlCapture.from_environment(attempt_id),
    )
    token = _CURRENT.set(diagnostics)
    try:
        yield diagnostics
    finally:
        _CURRENT.reset(token)


def current_auth_diagnostics() -> AuthDiagnostics:
    return _CURRENT.get()


def referenced_error(detail: str, diagnostics: AuthDiagnostics) -> str:
    return f"{detail} Reference: {diagnostics.attempt_id}."


def _enabled() -> bool:
    return os.getenv("LECTUREPILOT_AUTH_DIAGNOSTICS", "").strip().casefold() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _error_details(error: BaseException) -> dict[str, Any]:
    details: dict[str, Any] = {
        "exception_chain": _exception_chain(error),
        "traceback_frames": _traceback_frames(error),
    }
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    if isinstance(status, int):
        details["http_status"] = status
    url = getattr(response, "url", None)
    if isinstance(url, str):
        parsed = urlparse(url)
        if parsed.hostname:
            details["response_host"] = parsed.hostname
        if parsed.path:
            details["response_path"] = parsed.path[:240]
    return details


def _exception_chain(error: BaseException) -> list[str]:
    chain: list[str] = []
    current: BaseException | None = error
    while current is not None and len(chain) < 6:
        chain.append(type(current).__name__)
        current = current.__cause__ or current.__context__
    return chain


def _traceback_frames(error: BaseException) -> list[str]:
    frames: list[str] = []
    current: BaseException | None = error
    while current is not None and len(frames) < 16:
        traceback = current.__traceback__
        while traceback is not None and len(frames) < 16:
            frame = traceback.tb_frame
            module = str(frame.f_globals.get("__name__", "unknown"))
            frames.append(f"{module}:{frame.f_code.co_name}:{traceback.tb_lineno}")
            traceback = traceback.tb_next
        current = current.__cause__ or current.__context__
    return frames


def _safe_details(details: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in details.items():
        if isinstance(value, (bool, int, float)) or value is None:
            safe[key] = value
        elif isinstance(value, str):
            safe[key] = value[:160]
        elif isinstance(value, (list, tuple)):
            safe[key] = [str(item)[:120] for item in value[:24]]
    return safe
