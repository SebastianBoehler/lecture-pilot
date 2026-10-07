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


def test_critics_preserve_requested_reasoning_effort():
    result = native_model_settings(settings("openai/gpt-6"), reasoning_effort="medium")
    assert result["openai_reasoning_effort"] == "medium"
