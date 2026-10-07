import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects.postgresql import dialect

from lecturepilot.model_usage import complete_with_usage
from lecturepilot.model_usage_total import model_usage_total
from test_usage_quota_accounting import quota, scope


def response(input_tokens=100, output_tokens=20):
    return {"usage": {"prompt_tokens": input_tokens, "completion_tokens": output_tokens}}


async def test_successful_paid_requests_sum_including_parallel_native_calls():
    async def completion(**kwargs):
        await asyncio.sleep(0)
        return response(100, 20)

    with model_usage_total() as total:
        await asyncio.gather(
            *(complete_with_usage(None, completion, model="openai/test") for _ in range(3))
        )
        assert total.total_tokens == 360
    with model_usage_total() as isolated:
        assert isolated.total_tokens == 0


@pytest.mark.parametrize(
    "usage",
    [
        None,
        {},
        {"prompt_tokens": 10},
        {"prompt_tokens": -1, "completion_tokens": 5},
        {"prompt_tokens": True, "completion_tokens": 5},
        {"prompt_tokens": 10, "completion_tokens": "missing"},
        {"total_tokens": float("inf")},
    ],
)
async def test_missing_or_invalid_usage_keeps_full_quota_reservation(usage):
    async def completion(**kwargs):
        return SimpleNamespace(usage=usage)

    with model_usage_total() as total:
        await complete_with_usage(None, completion, model="openai/test")
        assert total.total_tokens is None
        q, database = quota()
        q.release_turn(**scope(), actual_tokens=total.total_tokens)
        statement = database.statements[0].compile(dialect=dialect())
        assert "reserved_tokens" not in str(statement)
        assert "active_turns" in str(statement)


async def test_unknown_attempt_remains_unknown_after_successful_retry(monkeypatch):
    calls = 0

    async def completion(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("Provider may have accepted the request.")
        return response()

    async def no_wait(seconds):
        pass

    monkeypatch.setattr("lecturepilot.model_usage.asyncio.sleep", no_wait)
    with model_usage_total() as total:
        await complete_with_usage(None, completion, model="openai/test")
        assert calls == 2
        assert total.tokens == 120
        assert total.total_tokens is None


async def test_cancelled_provider_request_keeps_reservation():
    entered = asyncio.Event()

    async def completion(**kwargs):
        entered.set()
        await asyncio.Event().wait()

    with model_usage_total() as total:
        task = asyncio.create_task(complete_with_usage(None, completion, model="openai/test"))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert total.total_tokens is None


@pytest.mark.parametrize(
    "usage",
    [
        {"input_tokens": 100, "output_tokens": 20},
        {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 0},
    ],
)
async def test_explicit_counters_never_refund_paid_tokens_as_zero(usage):
    async def completion(**kwargs):
        return {"usage": usage}

    with model_usage_total() as total:
        await complete_with_usage(None, completion, model="openai/test")
        assert total.total_tokens == 120
