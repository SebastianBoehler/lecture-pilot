from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError
from pydantic_ai.exceptions import ModelAPIError

from lecturepilot.model_provider_errors import (
    is_provider_timeout,
    is_retryable_provider_error,
    model_provider_error_message,
)
from lecturepilot.model_usage import complete_with_usage


def wrapped(cause):
    error = ModelAPIError(model_name="test", message="Provider request failed")
    error.__cause__ = cause
    return error


@pytest.mark.parametrize("error_type", [APIConnectionError, APITimeoutError])
@pytest.mark.asyncio
async def test_native_wrapped_transport_error_retries_then_succeeds(monkeypatch, error_type):
    calls = 0
    cause = error_type(request=httpx.Request("POST", "https://example.test"))

    async def completion(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise wrapped(cause)
        return SimpleNamespace(usage=None)

    async def no_wait(seconds):
        pass

    monkeypatch.setattr("lecturepilot.model_usage.asyncio.sleep", no_wait)
    await complete_with_usage(None, completion, model="openai/test-wrapped")
    assert calls == 2
    message = model_provider_error_message(wrapped(cause), provider="openai")
    assert "configuration" not in message
    assert "timed out" in message if error_type is APITimeoutError else "connection" in message
    assert is_provider_timeout(wrapped(cause)) is (error_type is APITimeoutError)


@pytest.mark.parametrize(
    ("error_type", "status", "body", "expected"),
    [
        (AuthenticationError, 401, {}, "credentials"),
        (RateLimitError, 429, {"code": "insufficient_quota"}, "credits are exhausted"),
    ],
)
def test_wrapped_permanent_errors_do_not_retry(error_type, status, body, expected):
    response = httpx.Response(status, request=httpx.Request("POST", "https://example.test"))
    error = wrapped(error_type("Provider error", response=response, body=body))
    assert not is_retryable_provider_error(error)
    assert expected in model_provider_error_message(error, provider="openai")


def test_cause_cycles_terminate_and_implicit_context_is_not_classified():
    error = RuntimeError("bad configuration")
    error.__cause__ = error
    error.__context__ = TimeoutError()
    assert not is_retryable_provider_error(error)
    assert not is_provider_timeout(error)
