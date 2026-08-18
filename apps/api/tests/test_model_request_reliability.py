from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from lecturepilot import model_rate_limits
from lecturepilot.model_request_options import (
    MODEL_REQUEST_TIMEOUT_SECONDS,
    completion_options,
)
from lecturepilot.model_usage import complete_with_usage
from lecturepilot.models import ProviderCapability, ProviderSettings


def test_completion_options_disable_hidden_retries_and_allow_long_structured_output() -> None:
    settings = ProviderSettings(
        provider="gemini",
        model="gemini/test-model",
        api_key_env="GEMINI_API_KEY",
        capabilities={ProviderCapability.CHAT},
    )

    options = completion_options(settings, temperature=0.2, max_tokens=100)

    assert options["timeout"] == MODEL_REQUEST_TIMEOUT_SECONDS
    assert options["timeout"] == 300
    assert options["max_retries"] == 0


def test_completion_options_allow_a_shorter_workload_circuit_breaker() -> None:
    settings = ProviderSettings(
        provider="openai",
        model="openai/gpt-5.6-luna",
        api_key_env="OPENAI_API_KEY",
        capabilities={ProviderCapability.CHAT},
    )

    options = completion_options(settings, temperature=0.2, timeout_seconds=60)

    assert options["timeout"] == 60


@pytest.mark.asyncio
async def test_timeout_retries_once_with_a_fresh_provider_request(monkeypatch) -> None:
    calls: list[dict] = []

    async def completion(**kwargs):
        calls.append(kwargs)
        raise TimeoutError("provider timeout")

    async def no_wait(_seconds: float) -> None:
        return None

    monkeypatch.setattr("lecturepilot.model_usage.asyncio.sleep", no_wait)

    with pytest.raises(TimeoutError, match="provider timeout"):
        await complete_with_usage(None, completion, model="gemini/test-model")

    assert calls == [
        {"model": "gemini/test-model"},
        {"model": "gemini/test-model"},
    ]


@pytest.mark.asyncio
async def test_long_request_can_disable_automatic_provider_retry(monkeypatch) -> None:
    calls = 0

    async def completion(**_kwargs):
        nonlocal calls
        calls += 1
        raise TimeoutError("provider timeout")

    async def no_wait(_seconds: float) -> None:
        raise AssertionError("single-attempt requests must not back off")

    monkeypatch.setattr("lecturepilot.model_usage.asyncio.sleep", no_wait)

    with pytest.raises(TimeoutError, match="provider timeout"):
        await complete_with_usage(
            None,
            completion,
            model="gemini/test-model",
            max_attempts=1,
        )

    assert calls == 1


@pytest.mark.asyncio
async def test_usage_guard_follows_the_requested_provider_timeout(monkeypatch) -> None:
    guarded: list[float] = []

    class TimeoutGuard:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *_args):
            return False

    def timeout(seconds: float) -> TimeoutGuard:
        guarded.append(seconds)
        return TimeoutGuard()

    async def completion(**_kwargs):
        return SimpleNamespace(usage=None)

    monkeypatch.setattr("lecturepilot.model_usage.asyncio.timeout", timeout)

    await complete_with_usage(None, completion, model="openai/test-model", timeout=60)

    assert guarded == [65]


@pytest.mark.asyncio
async def test_requests_for_one_model_share_a_concurrency_queue(monkeypatch) -> None:
    monkeypatch.setattr(model_rate_limits, "_conditions", {})
    monkeypatch.setattr(model_rate_limits, "_active_requests", {})
    monkeypatch.setattr(model_rate_limits, "_concurrency_limits", {})
    monkeypatch.setattr(model_rate_limits, "_blocked_until", {})
    active = 0
    peak_active = 0
    max_requests_started = asyncio.Event()
    release = asyncio.Event()

    async def completion(**_kwargs):
        nonlocal active, peak_active
        active += 1
        peak_active = max(peak_active, active)
        if active == model_rate_limits.MODEL_REQUEST_BOOTSTRAP_CONCURRENCY:
            max_requests_started.set()
        await release.wait()
        active -= 1
        return SimpleNamespace(usage=None)

    tasks = [
        asyncio.create_task(complete_with_usage(None, completion, model="openai/test-model"))
        for _ in range(model_rate_limits.MODEL_REQUEST_BOOTSTRAP_CONCURRENCY + 1)
    ]
    await asyncio.wait_for(max_requests_started.wait(), timeout=1)

    assert peak_active == model_rate_limits.MODEL_REQUEST_BOOTSTRAP_CONCURRENCY
    release.set()
    await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_rate_limit_retry_waits_for_provider_retry_after(monkeypatch) -> None:
    monkeypatch.setattr(model_rate_limits, "_conditions", {})
    monkeypatch.setattr(model_rate_limits, "_active_requests", {})
    monkeypatch.setattr(model_rate_limits, "_concurrency_limits", {})
    monkeypatch.setattr(model_rate_limits, "_blocked_until", {})
    waits: list[float] = []
    calls = 0
    now = 0.0

    async def completion(**_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise _RateLimitError()
        return SimpleNamespace(usage=None)

    async def record_wait(seconds: float) -> None:
        nonlocal now
        waits.append(seconds)
        now += seconds

    monkeypatch.setattr("lecturepilot.model_usage.asyncio.sleep", record_wait)
    monkeypatch.setattr("lecturepilot.model_usage.uniform", lambda _low, _high: 0.0)
    monkeypatch.setattr("lecturepilot.model_rate_limits.monotonic", lambda: now)

    await complete_with_usage(None, completion, model="openai/test-model")

    assert waits == [2.0]


@pytest.mark.asyncio
async def test_provider_headers_expand_concurrency_within_request_and_token_budgets(
    monkeypatch,
) -> None:
    monkeypatch.setattr(model_rate_limits, "_concurrency_limits", {})
    monkeypatch.setattr(model_rate_limits, "_average_tokens", {})

    model_rate_limits.observe_provider_response(
        "openai/test-model",
        SimpleNamespace(
            usage=SimpleNamespace(total_tokens=20_000),
            _hidden_params={
                "additional_headers": {
                    "x-ratelimit-remaining-requests": "4999",
                    "x-ratelimit-remaining-tokens": "4000000",
                }
            },
        ),
    )

    assert (
        model_rate_limits.current_model_concurrency("openai/test-model")
        == model_rate_limits.MODEL_REQUEST_MAX_CONCURRENCY
    )


@pytest.mark.asyncio
async def test_rate_limit_reset_supports_project_token_budget(monkeypatch) -> None:
    monkeypatch.setattr(model_rate_limits, "_blocked_until", {})
    monkeypatch.setattr("lecturepilot.model_rate_limits.monotonic", lambda: 10.0)

    delay = model_rate_limits.observe_provider_response(
        "openai/test-model",
        SimpleNamespace(
            _hidden_params={
                "additional_headers": {
                    "x-ratelimit-remaining-project-tokens": "0",
                    "x-ratelimit-reset-project-tokens": "1m30s",
                }
            }
        ),
    )

    assert delay == 90.0


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


@pytest.mark.asyncio
async def test_exhausted_provider_credits_are_not_retried(monkeypatch) -> None:
    calls = 0

    async def completion(**_kwargs):
        nonlocal calls
        calls += 1
        raise _QuotaError(
            "You have no credits remaining.",
            code="credit_balance_exhausted",
        )

    async def no_wait(_seconds: float) -> None:
        raise AssertionError("exhausted credits cannot recover through an immediate retry")

    monkeypatch.setattr("lecturepilot.model_usage.asyncio.sleep", no_wait)

    with pytest.raises(_QuotaError):
        await complete_with_usage(None, completion, model="openai/gpt-5.6-luna")

    assert calls == 1


class _QuotaError(RuntimeError):
    status_code = 429

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


class _RateLimitError(RuntimeError):
    status_code = 429
    headers = {"retry-after": "2", "x-ratelimit-reset-requests": "1s"}
