from __future__ import annotations

from types import SimpleNamespace

import pytest

from lecturepilot.model_request_options import (
    MODEL_REQUEST_TIMEOUT_SECONDS,
    completion_options,
)
from lecturepilot.model_usage import complete_with_usage
from lecturepilot.models import ProviderCapability, ProviderSettings


def test_completion_options_disable_hidden_retries_and_bound_timeout() -> None:
    settings = ProviderSettings(
        provider="gemini",
        model="gemini/test-model",
        api_key_env="GEMINI_API_KEY",
        capabilities={ProviderCapability.CHAT},
    )

    options = completion_options(settings, temperature=0.2, max_tokens=100)

    assert options["timeout"] == MODEL_REQUEST_TIMEOUT_SECONDS
    assert options["max_retries"] == 0


@pytest.mark.asyncio
async def test_transient_timeout_retries_once_with_same_request(monkeypatch) -> None:
    calls: list[dict] = []

    async def completion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise TimeoutError("provider timeout")
        return SimpleNamespace(usage=None)

    async def no_wait(_seconds: float) -> None:
        return None

    monkeypatch.setattr("lecturepilot.model_usage.asyncio.sleep", no_wait)

    result = await complete_with_usage(None, completion, model="gemini/test-model")

    assert result.usage is None
    assert calls == [
        {"model": "gemini/test-model"},
        {"model": "gemini/test-model"},
    ]


@pytest.mark.asyncio
async def test_nontransient_provider_error_is_not_retried(monkeypatch) -> None:
    calls = 0

    async def completion(**_kwargs):
        nonlocal calls
        calls += 1
        raise ValueError("invalid request")

    async def no_wait(_seconds: float) -> None:
        raise AssertionError("nontransient errors must not wait")

    monkeypatch.setattr("lecturepilot.model_usage.asyncio.sleep", no_wait)

    with pytest.raises(ValueError):
        await complete_with_usage(None, completion, model="gemini/test-model")

    assert calls == 1
