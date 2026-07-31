from types import ModuleType
import sys

import pytest

from lecturepilot.ppi_exam_source_service import PpiCredentialsError, _authenticated_client


def test_failed_ppi_login_closes_the_short_lived_client(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _RejectingClient()
    wrapper = ModuleType("tue_api_wrapper")
    wrapper.PpiClient = lambda: client  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tue_api_wrapper", wrapper)

    with pytest.raises(PpiCredentialsError):
        _authenticated_client("zxabc12", "wrong-password")

    assert client.closed is True


class _RejectingClient:
    def __init__(self) -> None:
        self.closed = False

    def login(self, username: str, password: str) -> None:
        raise PpiAuthenticationError

    def close(self) -> None:
        self.closed = True


class PpiAuthenticationError(Exception):
    pass
