"""Provider-compatible settings shared by native Pydantic AI agents."""

from lecturepilot.model_request_options import _is_openai_reasoning_model, tool_reasoning_effort
from lecturepilot.models import ProviderSettings


def native_model_settings(
    settings: ProviderSettings,
    *,
    temperature: float = 0.4,
    reasoning_effort: str = "low",
    timeout_seconds: float = 120,
    max_tokens: int = 16_000,
    tool_calls: bool = False,
) -> dict:
    options = {"timeout": timeout_seconds, "max_tokens": max_tokens}
    if settings.provider == "openai":
        options["openai_store"] = False
    if _is_openai_reasoning_model(settings):
        options["openai_reasoning_effort"] = (
            tool_reasoning_effort(settings) if tool_calls else reasoning_effort
        )
    else:
        options["temperature"] = temperature
    if tool_calls:
        options["parallel_tool_calls"] = True
    return options
