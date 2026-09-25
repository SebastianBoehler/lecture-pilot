from __future__ import annotations

from typing import Any

from lecturepilot.models import ProviderSettings


MODEL_REQUEST_TIMEOUT_SECONDS = 300
CANVAS_PLAN_REQUEST_TIMEOUT_SECONDS = 120
CANVAS_QUALITY_REQUEST_TIMEOUT_SECONDS = 120


def completion_options(
    settings: ProviderSettings,
    *,
    temperature: float,
    max_tokens: int | None = None,
    reasoning_effort: str | None = None,
    timeout_seconds: int = MODEL_REQUEST_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    options: dict[str, Any] = {
        "timeout": timeout_seconds,
        "max_retries": 0,
    }
    if _is_openai_reasoning_model(settings):
        if reasoning_effort:
            options["reasoning_effort"] = reasoning_effort
            if settings.model.split("/", 1)[-1].lower().startswith("gpt-6"):
                options["allowed_openai_params"] = ["reasoning_effort"]
    else:
        options["temperature"] = temperature
    if max_tokens is not None:
        options["max_tokens"] = max_tokens
    return options


def _is_openai_reasoning_model(settings: ProviderSettings) -> bool:
    if settings.provider != "openai":
        return False
    model_id = settings.model.split("/", 1)[-1].lower()
    return any(
        model_id == family or model_id.startswith((f"{family}-", f"{family}."))
        for family in ("gpt-5", "gpt-6")
    )


def tool_reasoning_effort(settings: ProviderSettings) -> str:
    if settings.provider == "openai" and settings.model.split("/", 1)[-1].lower().startswith("gpt-6"):
        return "none"
    return "low"
