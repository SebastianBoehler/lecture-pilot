"""Request-local usage totals for reconciling quota reservations."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class ModelUsageTotal:
    tokens: int = 0
    complete: bool = True

    @property
    def total_tokens(self) -> int | None:
        return self.tokens if self.complete else None


_total: ContextVar[ModelUsageTotal | None] = ContextVar("model_usage_total", default=None)


@contextmanager
def model_usage_total():
    total = ModelUsageTotal()
    token = _total.set(total)
    try:
        yield total
    finally:
        _total.reset(token)


def accumulate_model_usage(response, tokens: int) -> None:
    total = _total.get()
    if total is None:
        return
    usage = (
        response.get("usage") if isinstance(response, dict) else getattr(response, "usage", None)
    )
    if provider_usage_pair(usage) is None and not _valid_count(_value(usage, "total_tokens")):
        total.complete = False
    total.tokens += tokens


def mark_model_usage_unknown() -> None:
    total = _total.get()
    if total is not None:
        total.complete = False


def provider_usage_pair(usage):
    """Require both explicit nonnegative counters; absent usage is never zero usage."""
    for input_key, output_key in (
        ("input_tokens", "output_tokens"),
        ("prompt_tokens", "completion_tokens"),
    ):
        input_tokens, output_tokens = _value(usage, input_key), _value(usage, output_key)
        if input_tokens is not None or output_tokens is not None:
            return (
                (input_tokens, output_tokens)
                if _valid_count(input_tokens) and _valid_count(output_tokens)
                else None
            )
    return None


def _value(value, name):
    return value.get(name) if isinstance(value, dict) else getattr(value, name, None)


def _valid_count(value):
    return type(value) is int and value >= 0
