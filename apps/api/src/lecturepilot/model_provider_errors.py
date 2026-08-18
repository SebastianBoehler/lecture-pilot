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
    status_code = getattr(exc, "status_code", None)
    error_name = type(exc).__name__.casefold()
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
    if status_code in {401, 403}:
        return f"{name} rejected the configured API credentials. Check the provider key."
    return f"{name} rejected the model request. Check the model configuration."


def is_retryable_provider_error(exc: Exception) -> bool:
    if _credits_exhausted(exc):
        return False
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    status_code = getattr(exc, "status_code", None)
    if status_code in {408, 409, 429, 500, 502, 503, 504}:
        return True
    name = type(exc).__name__.lower()
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
    if isinstance(exc, TimeoutError) or getattr(exc, "status_code", None) == 408:
        return True
    return "timeout" in type(exc).__name__.casefold()


def _credits_exhausted(exc: Exception) -> bool:
    text = " ".join(
        _error_text(value)
        for value in (
            exc,
            getattr(exc, "code", None),
            getattr(exc, "body", None),
            getattr(exc, "detail", None),
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
