from __future__ import annotations

import json
import logging
from types import SimpleNamespace

from lecturepilot.auth_diagnostics import (
    AUTH_DIAGNOSTIC_LOGGER,
    AUTH_DIAGNOSTIC_PREFIX,
    auth_diagnostic_attempt,
)


def test_disabled_auth_diagnostics_emit_nothing(monkeypatch, caplog) -> None:
    monkeypatch.delenv("LECTUREPILOT_AUTH_DIAGNOSTICS", raising=False)

    with caplog.at_level(logging.WARNING, logger=AUTH_DIAGNOSTIC_LOGGER):
        with auth_diagnostic_attempt("professor01") as diagnostics:
            started = diagnostics.started("alma.profile")
            diagnostics.succeeded("alma.profile", started, current_role="lecturer")

    assert caplog.messages == []


def test_enabled_auth_diagnostics_are_correlated_and_redacted(monkeypatch, caplog) -> None:
    monkeypatch.setenv("LECTUREPILOT_AUTH_DIAGNOSTICS", "true")
    try:
        raise RuntimeError("secret provider response")
    except RuntimeError as exc:
        error = exc
    error.response = SimpleNamespace(  # type: ignore[attr-defined]
        status_code=503,
        url="https://alma.example/profile?token=must-not-appear",
    )

    with caplog.at_level(logging.WARNING, logger=AUTH_DIAGNOSTIC_LOGGER):
        with auth_diagnostic_attempt("professor01") as diagnostics:
            role_started = diagnostics.started("alma.profile")
            diagnostics.succeeded(
                "alma.profile",
                role_started,
                current_role="lecturer",
                available_roles=["lecturer", "examiner"],
            )
            failure_started = diagnostics.started("alma.timetable")
            diagnostics.failed("alma.timetable", failure_started, error)

    events = [_event(message) for message in caplog.messages]
    assert {event["attempt_id"] for event in events} == {diagnostics.attempt_id}
    assert events[-1]["exception_chain"] == ["RuntimeError"]
    assert events[-1]["http_status"] == 503
    assert events[-1]["response_host"] == "alma.example"
    assert events[-1]["response_path"] == "/profile"
    assert any("test_enabled_auth_diagnostics" in frame for frame in events[-1]["traceback_frames"])
    serialized = "\n".join(caplog.messages)
    assert "professor01" not in serialized
    assert "secret provider response" not in serialized
    assert "must-not-appear" not in serialized


def _event(message: str) -> dict:
    assert message.startswith(AUTH_DIAGNOSTIC_PREFIX)
    return json.loads(message.removeprefix(AUTH_DIAGNOSTIC_PREFIX))
