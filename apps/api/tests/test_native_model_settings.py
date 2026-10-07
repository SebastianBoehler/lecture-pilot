from lecturepilot.native_model_settings import native_model_settings
from lecturepilot.models import ProviderSettings


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


def test_openai_prompt_cache_key_is_stable_per_course_and_lecture():
    from lecturepilot.native_model_settings import tutor_prompt_cache_key

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
    google = native_model_settings(
        settings("gemini/gemini-3.1-flash-lite"), prompt_cache_key="lp:should-not-apply"
    )
    assert "openai_prompt_cache_key" not in google


def test_tutor_output_caps_drop_when_the_turn_cannot_write():
    from lecturepilot.native_tutor import tutor_output_limits

    assert tutor_output_limits(writing_tools=False) == (1_500, 4_096)
    max_tokens, output_limit = tutor_output_limits(writing_tools=True)
    assert max_tokens == 8_192
    assert output_limit < 32_768


def test_critics_preserve_requested_reasoning_effort():
    result = native_model_settings(settings("openai/gpt-6"), reasoning_effort="medium")
    assert result["openai_reasoning_effort"] == "medium"
