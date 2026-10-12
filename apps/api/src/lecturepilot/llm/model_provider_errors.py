from __future__ import annotations

from typing import Any


_CREDIT_MARKERS = (
    "credit_balance_exhausted",
    "insufficient_quota",
    "no credits remaining",
    "insufficient credits",
)


def model_provider_error_message(
    exc: Exception,
    *,
    provider: str,
    attempts: int = 2,
) -> str:
    name = _provider_name(provider)
    if _credits_exhausted(exc):
        return (
            f"{name} API credits are exhausted. "
            "Add credits to the configured provider account, then retry this request."
        )
    status_code = _status_code(exc)
    error_name = " ".join(type(error).__name__.casefold() for error in _causes(exc))
    if is_provider_timeout(exc):
        return (
            f"{name} model request timed out before completing. "
            "The request can be retried without regenerating completed lectures."
        )
    if status_code == 429 or "ratelimit" in error_name:
        return (
            f"{name} rate limit was still active after {attempts} attempts. "
            "LecturePilot queued requests conservatively; retry this lecture after the reset."
        )
    if status_code in {500, 502, 503, 504}:
        return (
            f"{name} returned a temporary service error after {attempts} attempts. "
            "Retry this lecture; completed lectures are preserved."
        )
    if _is_connection_error(exc):
        return (
            f"{name} model connection failed before completing. "
            "Retry this lecture; completed lectures are preserved."
        )
    if status_code in {401, 403}:
        return f"{name} rejected the configured API credentials. Check the provider key."
    return f"{name} rejected the model request. Check the model configuration."


def is_retryable_provider_error(exc: Exception) -> bool:
    if _credits_exhausted(exc):
        return False
    if is_provider_timeout(exc) or _is_connection_error(exc):
        return True
    status_code = _status_code(exc)
    if status_code in {408, 409, 429, 500, 502, 503, 504}:
        return True
    name = " ".join(type(error).__name__.casefold() for error in _causes(exc))
    return any(
        marker in name
        for marker in (
            "timeout",
            "ratelimit",
            "serviceunavailable",
            "apiconnection",
            "internalserver",
        )
    )


def is_provider_timeout(exc: Exception) -> bool:
    return any(
        isinstance(error, TimeoutError)
        or getattr(error, "status_code", None) == 408
        or "timeout" in type(error).__name__.casefold()
        for error in _causes(exc)
    )


def _is_connection_error(exc: Exception) -> bool:
    return any(
        isinstance(error, ConnectionError) or "apiconnection" in type(error).__name__.casefold()
        for error in _causes(exc)
    )


def _causes(exc: Exception):
    seen: set[int] = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        yield exc
        exc = exc.__cause__


def _status_code(exc: Exception):
    return next(
        (
            code
            for error in _causes(exc)
            if (code := getattr(error, "status_code", None)) is not None
        ),
        None,
    )


def _credits_exhausted(exc: Exception) -> bool:
    text = " ".join(
        _error_text(value)
        for error in _causes(exc)
        for value in (
            error,
            getattr(error, "code", None),
            getattr(error, "body", None),
            getattr(error, "detail", None),
        )
    ).casefold()
    return any(marker in text for marker in _CREDIT_MARKERS)


def _error_text(value: Any) -> str:
    return "" if value is None else str(value)


def _provider_name(provider: str) -> str:
    return {
        "gemini": "Gemini",
        "google": "Gemini",
        "openai": "OpenAI",
        "openrouter": "OpenRouter",
    }.get(provider.casefold(), "Model provider")
