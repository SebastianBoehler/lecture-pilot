from __future__ import annotations

import io

import lecturepilot.core.runtime_readiness as readiness_module
from lecturepilot.core.runtime_readiness import RuntimeReadiness


class _Database:
    def __init__(self, *, fails: bool = False) -> None:
        self.fails = fails

    def ping(self) -> None:
        if self.fails:
            raise RuntimeError("private database endpoint")


class _Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        self.close()


def test_runtime_readiness_checks_database_and_compiler(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_LATEX_COMPILER_URL", "http://compiler:8080")
    monkeypatch.setattr(
        readiness_module,
        "urlopen",
        lambda request, timeout: _Response(b'{"status":"ok"}'),
    )

    result = RuntimeReadiness(_Database()).check()

    assert result.ready
    assert result.checks == {"database": "ok", "latex_compiler": "ok"}


def test_stopped_document_converter_does_not_gate_readiness(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_LATEX_COMPILER_URL", "http://compiler:8080")
    monkeypatch.setenv("LECTUREPILOT_DOCUMENT_CONVERTER_URL", "http://converter:8080")
    requested = []

    def urlopen(request, timeout):
        requested.append(request.full_url)
        return _Response(b'{"status":"ok"}')

    monkeypatch.setattr(readiness_module, "urlopen", urlopen)

    assert RuntimeReadiness(_Database()).check().ready
    assert requested == ["http://compiler:8080/health"]


def test_runtime_readiness_reports_only_dependency_state(monkeypatch) -> None:
    monkeypatch.delenv("LECTUREPILOT_LATEX_COMPILER_URL", raising=False)

    result = RuntimeReadiness(_Database(fails=True)).check()

    assert not result.ready
    assert result.checks == {"database": "error", "latex_compiler": "error"}
