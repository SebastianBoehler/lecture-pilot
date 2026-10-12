from lecturepilot.llm.native_model_settings import native_model_settings
from lecturepilot.core.models import ProviderSettings


def settings(model):
    provider = model.partition("/")[0]
    return ProviderSettings(provider=provider, model=model, api_key_env="KEY", capabilities=set())


def test_gpt6_tools_use_none_reasoning_and_never_temperature():
    result = native_model_settings(settings("openai/gpt-6"), tool_calls=True)
    assert result["openai_reasoning_effort"] == "none"
    assert result["openai_store"] is False
    assert "temperature" not in result
    assert result["max_tokens"] == 16_000


def test_non_reasoning_openai_and_google_accept_temperature():
    for model in ["openai/gpt-4.1", "gemini/gemini-3.1-flash-lite"]:
        result = native_model_settings(settings(model), temperature=0.0)
        assert result["temperature"] == 0.0
        assert "openai_reasoning_effort" not in result


def test_prompt_cache_key_is_stable_per_course_and_lecture():
    from lecturepilot.llm.native_model_settings import tutor_prompt_cache_key

    key = tutor_prompt_cache_key(
        settings("openai/gpt-6"),
        course_id="course-1",
        lecture_id="lecture-1",
        publication_version=4,
    )
    assert key == "lp:openai/gpt-6:course-1:lecture-1:4"
    assert "student" not in key
    result = native_model_settings(settings("openai/gpt-6"), prompt_cache_key=key)
    assert result["openai_prompt_cache_key"] == key
    assert (
        tutor_prompt_cache_key(
            settings("gemini/gemini-3.1-flash-lite"),
            course_id="course-1",
            lecture_id="lecture-1",
            publication_version=4,
        )
        is None
    )
    assert (
        tutor_prompt_cache_key(
            settings("openrouter/anthropic/claude-x"),
            course_id="course-1",
            lecture_id="lecture-1",
            publication_version=4,
        )
        == "lp:openrouter/anthropic/claude-x:course-1:lecture-1:4"
    )
    router = native_model_settings(settings("openrouter/anthropic/claude-x"), prompt_cache_key=key)
    assert router["openai_prompt_cache_key"] == key
    assert router["openrouter_cache_instructions"] is True
    assert router["openrouter_cache_tool_definitions"] is True
    assert router["openrouter_cache_messages"] is True
    assert "openrouter_cache_instructions" not in native_model_settings(
        settings("openrouter/anthropic/claude-x")
    )
    google = native_model_settings(
        settings("gemini/gemini-3.1-flash-lite"), prompt_cache_key="lp:should-not-apply"
    )
    assert "openai_prompt_cache_key" not in google


def test_critics_preserve_requested_reasoning_effort():
    result = native_model_settings(settings("openai/gpt-6"), reasoning_effort="medium")
    assert result["openai_reasoning_effort"] == "medium"
