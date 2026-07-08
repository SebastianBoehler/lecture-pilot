from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def local_dev_auth_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_ENV", "test")
    monkeypatch.setenv("LECTUREPILOT_AUTH_MODE", "dev")
