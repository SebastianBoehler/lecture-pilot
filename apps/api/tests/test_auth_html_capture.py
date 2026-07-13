from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from lecturepilot.auth_diagnostics import (
    AUTH_DIAGNOSTIC_LOGGER,
    auth_diagnostic_attempt,
)
from lecturepilot.tuebingen_html_capture import _prepare_authenticated_client


def test_html_capture_writes_plain_response_under_attempt_id(
    monkeypatch,
    tmp_path: Path,
    caplog,
) -> None:
    monkeypatch.setenv("LECTUREPILOT_AUTH_DIAGNOSTICS", "true")
    monkeypatch.setenv("LECTUREPILOT_AUTH_CAPTURE_HTML", "true")
    monkeypatch.setenv("LECTUREPILOT_WORKSPACE_ROOT", str(tmp_path))
    html = "<!doctype html><html><body>Professor role page</body></html>"
    response = _response(html, provider_url="https://alma.example/profile", status=200)

    with caplog.at_level(logging.WARNING, logger=AUTH_DIAGNOSTIC_LOGGER):
        with auth_diagnostic_attempt("professor01") as diagnostics:
            diagnostics.response_hook("alma")(response)

    capture_dir = tmp_path / "auth-diagnostics" / diagnostics.attempt_id
    captures = list(capture_dir.glob("*.html"))
    assert [path.name for path in captures] == ["001-alma-get-200.html"]
    assert captures[0].read_text(encoding="utf-8") == html
    assert any('"step":"auth.html_capture"' in message for message in caplog.messages)
    assert html not in "\n".join(caplog.messages)


def test_html_capture_ignores_non_html_responses(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LECTUREPILOT_AUTH_CAPTURE_HTML", "true")
    monkeypatch.setenv("LECTUREPILOT_WORKSPACE_ROOT", str(tmp_path))
    response = _response(
        "BEGIN:VCALENDAR\nEND:VCALENDAR",
        provider_url="https://alma.example/calendar.ics",
        status=200,
        content_type="text/calendar",
    )

    with auth_diagnostic_attempt("student01") as diagnostics:
        diagnostics.response_hook("alma")(response)

    capture_dir = tmp_path / "auth-diagnostics" / diagnostics.attempt_id
    assert not capture_dir.exists()


def test_provider_login_error_html_is_captured_before_exception(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LECTUREPILOT_AUTH_CAPTURE_HTML", "true")
    monkeypatch.setenv("LECTUREPILOT_WORKSPACE_ROOT", str(tmp_path))
    api = SimpleNamespace(
        _client=None,
        credentials=SimpleNamespace(username="professor01", password="secret"),
    )

    with auth_diagnostic_attempt("professor01") as diagnostics:
        with pytest.raises(RuntimeError, match="Unexpected professor login page"):
            _prepare_authenticated_client(api, _FailingClient, "alma", diagnostics)

    capture_dir = tmp_path / "auth-diagnostics" / diagnostics.attempt_id
    captures = list(capture_dir.glob("*.html"))
    assert [path.name for path in captures] == ["001-alma-post-200.html"]
    assert "unrecognized-role" in captures[0].read_text(encoding="utf-8")


def _response(
    html: str,
    *,
    provider_url: str,
    status: int,
    content_type: str = "text/html; charset=utf-8",
):
    return SimpleNamespace(
        text=html,
        url=provider_url,
        status_code=status,
        headers={"content-type": content_type},
        request=SimpleNamespace(method="GET"),
    )


class _FailingClient:
    def __init__(self) -> None:
        self.session = _HookSession()

    def login(self, _username: str, _password: str) -> None:
        response = _response(
            "<html><body data-role='unrecognized-role'></body></html>",
            provider_url="https://alma.example/login",
            status=200,
        )
        response.request.method = "POST"
        for hook in self.session.hooks["response"]:
            hook(response)
        raise RuntimeError("Unexpected professor login page")


class _HookSession:
    def __init__(self) -> None:
        self.hooks: dict[str, list] = {"response": []}
        self.closed = False

    def close(self) -> None:
        self.closed = True
