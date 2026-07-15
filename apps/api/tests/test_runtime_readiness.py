from __future__ import annotations

import io

import lecturepilot.runtime_readiness as readiness_module
from lecturepilot.runtime_readiness import RuntimeReadiness


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


def test_runtime_readiness_reports_only_dependency_state(monkeypatch) -> None:
    monkeypatch.delenv("LECTUREPILOT_LATEX_COMPILER_URL", raising=False)

    result = RuntimeReadiness(_Database(fails=True)).check()

    assert not result.ready
    assert result.checks == {"database": "error", "latex_compiler": "error"}
