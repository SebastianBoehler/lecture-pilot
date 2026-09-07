from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
import re
from time import monotonic
from typing import Any


DEFAULT_REQUEST_TOKEN_ESTIMATE = 32_000
_conditions: dict[tuple[int, str], asyncio.Condition] = {}
_active_requests: dict[tuple[int, str], int] = {}
_concurrency_limits: dict[tuple[int, str], int] = {}
_average_tokens: dict[tuple[int, str], float] = {}
_blocked_until: dict[tuple[int, str], float] = {}


@asynccontextmanager
async def model_request_slot(model: str) -> AsyncIterator[None]:
    key = (id(asyncio.get_running_loop()), model)
    condition = _conditions.setdefault(key, asyncio.Condition())
    while True:
        await _wait_until_unblocked(key)
        async with condition:
            active = _active_requests.get(key, 0)
            limit = _concurrency_limits.get(key)
            if limit is None or active < limit:
                _active_requests[key] = active + 1
                break
            await condition.wait()
    try:
        yield
    finally:
        async with condition:
            _active_requests[key] = max(0, _active_requests.get(key, 1) - 1)
            condition.notify_all()


def observe_provider_response(model: str, value: Any) -> float:
    """Record provider cooldown metadata and return the required retry delay."""
    key = (id(asyncio.get_running_loop()), model)
    headers = provider_headers(value)
    retry_after = _duration(headers.get("retry-after"))
    reset_requests = _duration(headers.get("x-ratelimit-reset-requests"))
    reset_tokens = max(
        _duration(headers.get("x-ratelimit-reset-tokens")),
        _duration(headers.get("x-ratelimit-reset-project-tokens")),
    )
    exhausted = (
        _is_zero(headers.get("x-ratelimit-remaining-requests"))
        or _is_zero(headers.get("x-ratelimit-remaining-tokens"))
        or _is_zero(headers.get("x-ratelimit-remaining-project-tokens"))
    )
    is_rate_limited = getattr(value, "status_code", None) == 429
    delay = max(
        retry_after,
        reset_requests if exhausted or is_rate_limited else 0.0,
        reset_tokens if exhausted else 0.0,
    )
    if delay > 0:
        _blocked_until[key] = max(_blocked_until.get(key, 0.0), monotonic() + delay)
    _observe_concurrency_budget(key, headers, value)
    return delay


def current_model_concurrency(model: str) -> int | None:
    key = (id(asyncio.get_running_loop()), model)
    return _concurrency_limits.get(key)


def provider_headers(value: Any) -> dict[str, str]:
    sources = [
        getattr(value, "headers", None),
        getattr(getattr(value, "response", None), "headers", None),
        getattr(value, "_hidden_params", None),
    ]
    headers: dict[str, str] = {}
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        nested = source.get("headers") or source.get("additional_headers")
        if isinstance(nested, Mapping):
            source = nested
        for key, item in source.items():
            if isinstance(key, str) and isinstance(item, (str, int, float)):
                headers[key.lower()] = str(item)
    return headers


async def _wait_until_unblocked(key: tuple[int, str]) -> None:
    delay = _blocked_until.get(key, 0.0) - monotonic()
    if delay > 0:
        await asyncio.sleep(delay)


def _observe_concurrency_budget(
    key: tuple[int, str],
    headers: dict[str, str],
    value: Any,
) -> None:
    used_tokens = _usage_tokens(value)
    if used_tokens > 0:
        previous = _average_tokens.get(key, float(used_tokens))
        _average_tokens[key] = previous * 0.75 + used_tokens * 0.25
    requests = _positive_int(headers.get("x-ratelimit-remaining-requests"))
    token_values = [
        value
        for value in (
            _positive_int(headers.get("x-ratelimit-remaining-tokens")),
            _positive_int(headers.get("x-ratelimit-remaining-project-tokens")),
        )
        if value is not None
    ]
    if requests is None and not token_values:
        return
    candidates: list[int] = []
    if requests is not None:
        candidates.append(requests)
    if token_values:
        estimate = max(1, round(_average_tokens.get(key, DEFAULT_REQUEST_TOKEN_ESTIMATE)))
        candidates.append(min(token_values) // estimate)
    _concurrency_limits[key] = max(1, min(candidates))
    _notify_waiters(key)


def _usage_tokens(value: Any) -> int:
    usage = getattr(value, "usage", None)
    if isinstance(value, Mapping):
        usage = value.get("usage", usage)
    if isinstance(usage, Mapping):
        usage = usage.get("total_tokens") or (
            (_positive_int(str(usage.get("input_tokens", usage.get("prompt_tokens")))) or 0)
            + (_positive_int(str(usage.get("output_tokens", usage.get("completion_tokens")))) or 0)
        )
    else:
        usage = getattr(usage, "total_tokens", None)
    return _positive_int(str(usage)) or 0


def _positive_int(value: str | None) -> int | None:
    try:
        parsed = int(value or "")
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _notify_waiters(key: tuple[int, str]) -> None:
    condition = _conditions.get(key)
    if condition is None:
        return

    async def notify() -> None:
        async with condition:
            condition.notify_all()

    asyncio.get_running_loop().create_task(notify())


def _duration(value: str | None) -> float:
    if not value:
        return 0.0
    text = value.strip().lower().replace(" ", "")
    parts = re.findall(r"(\d+(?:\.\d+)?)(ms|s|m|h)", text)
    if parts and "".join(f"{number}{unit}" for number, unit in parts) == text:
        multipliers = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}
        return sum(float(number) * multipliers[unit] for number, unit in parts)
    try:
        return max(0.0, float(text))
    except ValueError:
        return 0.0


def _is_zero(value: str | None) -> bool:
    try:
        return int(value or "1") <= 0
    except ValueError:
        return False
