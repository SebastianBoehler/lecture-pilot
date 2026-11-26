"""Provider-compatible settings shared by native Pydantic AI agents."""

from hashlib import sha256

from lecturepilot.llm.model_request_options import _is_openai_reasoning_model, tool_reasoning_effort
from lecturepilot.core.models import ProviderSettings

_PROMPT_CACHE_KEY_PROVIDERS = {"openai", "openrouter"}


def tutor_prompt_cache_key(
    settings: ProviderSettings,
    *,
    course_id: str,
    lecture_id: str,
    publication_version: int | None,
    recall_section: str | None = None,
) -> str | None:
    """Stable across learners and turns. User id is omitted so shared prefixes can hit.

    OpenAI uses it to route equal prefixes to one cache; OpenRouter uses it as its sticky
    routing key so a lecture's requests reach the same downstream provider cache.
    """
    if settings.provider not in _PROMPT_CACHE_KEY_PROVIDERS:
        return None
    version = 0 if publication_version is None else publication_version
    lecture_key = f"lp:{settings.model}:{course_id}:{lecture_id}:{version}"
    if recall_section is not None:
        digest = sha256(f"{lecture_key}:recall:{recall_section}".encode()).hexdigest()[:40]
        return f"lp:recall:{digest}"
    return lecture_key


def native_model_settings(
    settings: ProviderSettings,
    *,
    temperature: float = 0.4,
    reasoning_effort: str = "low",
    timeout_seconds: float = 120,
    max_tokens: int = 16_000,
    tool_calls: bool = False,
    prompt_cache_key: str | None = None,
) -> dict:
    options = {"timeout": timeout_seconds, "max_tokens": max_tokens}
    if settings.provider == "openai":
        options["openai_store"] = False
    if prompt_cache_key and settings.provider in _PROMPT_CACHE_KEY_PROVIDERS:
        options["openai_prompt_cache_key"] = prompt_cache_key
    if prompt_cache_key and settings.provider == "openrouter":
        # Downstream providers without automatic caching (Anthropic) need explicit
        # breakpoints: tools, static instructions, the last message for the tool loop and a
        # CachePoint after the shared lecture context. Others ignore these markers.
        options["openrouter_cache_tool_definitions"] = True
        options["openrouter_cache_instructions"] = True
        options["openrouter_cache_messages"] = True
    if _is_openai_reasoning_model(settings):
        options["openai_reasoning_effort"] = (
            tool_reasoning_effort(settings) if tool_calls else reasoning_effort
        )
    else:
        options["temperature"] = temperature
    if tool_calls:
        options["parallel_tool_calls"] = True
    return options
