import asyncio
from types import SimpleNamespace

import pytest

from lecturepilot import model_rate_limits
from lecturepilot.model_usage import complete_with_usage


@pytest.mark.asyncio
async def test_provider_budget_still_limits_in_flight_requests(monkeypatch):
    for name in (
        "_conditions",
        "_active_requests",
        "_concurrency_limits",
        "_average_tokens",
        "_blocked_until",
    ):
        monkeypatch.setattr(model_rate_limits, name, {})
    model_rate_limits.observe_provider_response(
        "openai/budget",
        SimpleNamespace(
            headers={"x-ratelimit-remaining-requests": "2"},
            usage=None,
        ),
    )
    release = asyncio.Event()
    started = asyncio.Event()
    active = peak = 0

    async def completion(**kwargs):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        if active == 2:
            started.set()
        await release.wait()
        active -= 1
        return SimpleNamespace(usage=None)

    tasks = [
        asyncio.create_task(complete_with_usage(None, completion, model="openai/budget"))
        for _ in range(6)
    ]
    await asyncio.wait_for(started.wait(), 1)
    assert peak == 2
    release.set()
    await asyncio.gather(*tasks)
    assert peak == 2


@pytest.mark.asyncio
async def test_native_usage_calibrates_token_budget_without_an_application_ceiling(monkeypatch):
    monkeypatch.setattr(model_rate_limits, "_concurrency_limits", {})
    monkeypatch.setattr(model_rate_limits, "_average_tokens", {})
    model_rate_limits.observe_provider_response(
        "openai/native",
        {
            "usage": {"prompt_tokens": 15000, "completion_tokens": 5000},
        },
    )
    model_rate_limits.observe_provider_response(
        "openai/native",
        SimpleNamespace(
            headers={"x-ratelimit-remaining-tokens": "4000000"},
        ),
    )
    assert model_rate_limits.current_model_concurrency("openai/native") == 200
