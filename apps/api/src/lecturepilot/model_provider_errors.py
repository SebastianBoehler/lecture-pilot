from __future__ import annotations

from typing import Any


_CREDIT_MARKERS = (
    "credit_balance_exhausted",
    "insufficient_quota",
    "no credits remaining",
    "insufficient credits",
)


def model_provider_error_message(exc: Exception, *, provider: str) -> str:
    if _credits_exhausted(exc):
        return (
            f"{_provider_name(provider)} API credits are exhausted. "
            "Add credits to the configured provider account, then retry this tutor message."
        )
    return "Model request failed. Check the provider key and model configuration."


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
