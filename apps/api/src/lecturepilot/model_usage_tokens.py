"""Normalize provider usage counters without fabricating missing usage."""

from typing import Any

from lecturepilot.model_usage_total import provider_usage_pair


def usage_tokens_from_response(response: Any) -> dict[str, int]:
    usage = _value(response, "usage")
    prompt_details = _value(usage, "prompt_tokens_details")
    completion_details = _value(usage, "completion_tokens_details")
    counters = provider_usage_pair(usage)
    input_tokens, output_tokens = counters or (
        _nonnegative(_value(usage, "prompt_tokens")),
        _nonnegative(_value(usage, "completion_tokens")),
    )
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": max(
            _nonnegative(_value(usage, "total_tokens")), input_tokens + output_tokens
        ),
        "cached_input_tokens": _nonnegative(_value(prompt_details, "cached_tokens")),
        "reasoning_tokens": _nonnegative(_value(completion_details, "reasoning_tokens")),
    }


def _empty_tokens() -> dict[str, int]:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cached_input_tokens": 0,
        "reasoning_tokens": 0,
    }


def _value(value: Any, name: str) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _nonnegative(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError, OverflowError):
        return 0
