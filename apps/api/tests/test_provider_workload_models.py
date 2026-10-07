import pytest

from lecturepilot.models import ProviderSettings
from lecturepilot.providers import workload_settings, ProviderConfigurationError


@pytest.fixture
def primary():
    return ProviderSettings(
        provider="openai", model="openai/main", api_key_env="OPENAI_API_KEY", capabilities=set()
    )


def test_unset_tiers_preserve_explicit_primary_model(primary, monkeypatch):
    monkeypatch.delenv("LECTUREPILOT_UTILITY_MODEL", raising=False)
    monkeypatch.delenv("LECTUREPILOT_CRITIC_MODEL", raising=False)
    assert workload_settings(primary, "utility") is primary
    assert workload_settings(primary, "critic") is primary


def test_utility_model_requires_allowlist_and_its_own_credential(primary, monkeypatch):
    monkeypatch.setenv("LECTUREPILOT_UTILITY_MODEL", "gemini/utility")
    monkeypatch.setenv("LECTUREPILOT_ALLOWED_MODELS", "openai/main")
    with pytest.raises(ProviderConfigurationError, match="not allowed"):
        workload_settings(primary, "utility")
    monkeypatch.setenv("LECTUREPILOT_ALLOWED_MODELS", "openai/main,gemini/utility")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ProviderConfigurationError, match="GEMINI_API_KEY"):
        workload_settings(primary, "utility")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert workload_settings(primary, "utility").model == "gemini/utility"


def test_critic_tier_selects_only_the_configured_model(primary, monkeypatch):
    monkeypatch.setenv("LECTUREPILOT_CRITIC_MODEL", "openai/critic")
    monkeypatch.setenv("LECTUREPILOT_ALLOWED_MODELS", "openai/main,openai/critic")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert workload_settings(primary, "critic").model == "openai/critic"
