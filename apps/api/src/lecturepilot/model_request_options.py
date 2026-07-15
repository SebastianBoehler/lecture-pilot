from __future__ import annotations

from typing import Any

from lecturepilot.models import ProviderSettings


MODEL_REQUEST_TIMEOUT_SECONDS = 120


def completion_options(
    settings: ProviderSettings,
    *,
    temperature: float,
    max_tokens: int | None = None,
    reasoning_effort: str | None = None,
) -> dict[str, Any]:
    options: dict[str, Any] = {
        "timeout": MODEL_REQUEST_TIMEOUT_SECONDS,
        "max_retries": 0,
    }
    if _is_openai_gpt5(settings):
        if reasoning_effort:
            options["reasoning_effort"] = reasoning_effort
    else:
        options["temperature"] = temperature
    if max_tokens is not None:
        options["max_tokens"] = max_tokens
    return options


def _is_openai_gpt5(settings: ProviderSettings) -> bool:
    if settings.provider != "openai":
        return False
    model_id = settings.model.split("/", 1)[-1].lower()
    return model_id == "gpt-5" or model_id.startswith("gpt-5-") or model_id.startswith("gpt-5.")
