from __future__ import annotations

from lecturepilot.models import ProviderSettings


MODEL_REQUEST_TIMEOUT_SECONDS = 300
CANVAS_PLAN_REQUEST_TIMEOUT_SECONDS = 120
CANVAS_QUALITY_REQUEST_TIMEOUT_SECONDS = 120


def _is_openai_reasoning_model(settings: ProviderSettings) -> bool:
    if settings.provider != "openai":
        return False
    model_id = settings.model.split("/", 1)[-1].lower()
    return any(
        model_id == family or model_id.startswith((f"{family}-", f"{family}."))
        for family in ("gpt-5", "gpt-6")
    )


def tool_reasoning_effort(settings: ProviderSettings) -> str:
    if settings.provider == "openai" and settings.model.split("/", 1)[-1].lower().startswith(
        "gpt-6"
    ):
        return "none"
    return "low"
