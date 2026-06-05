import pytest

from lecturepilot.models import ProviderCapability
from lecturepilot.providers import ProviderConfigurationError, ProviderRegistry


def test_provider_registry_reports_missing_required_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    registry = ProviderRegistry.from_env(model="openrouter/z-ai/glm-5.1")

    with pytest.raises(ProviderConfigurationError, match="OPENROUTER_API_KEY"):
        registry.require_ready([ProviderCapability.CHAT])


def test_provider_registry_accepts_configured_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    registry = ProviderRegistry.from_env(model="openrouter/z-ai/glm-5.1")

    settings = registry.require_ready([ProviderCapability.CHAT])

    assert settings.provider == "openrouter"
    assert settings.model == "openrouter/z-ai/glm-5.1"
    assert settings.api_key_env == "OPENROUTER_API_KEY"
