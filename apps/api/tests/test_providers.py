import pytest

from lecturepilot.models import ProviderCapability
from lecturepilot.providers import DEFAULT_MODEL, ProviderConfigurationError, ProviderRegistry


def test_provider_registry_defaults_to_gemini_flash_lite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LECTUREPILOT_MODEL", raising=False)
    registry = ProviderRegistry.from_env()

    assert registry.model == DEFAULT_MODEL
    assert registry.provider == "gemini"


def test_provider_registry_reports_missing_required_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    registry = ProviderRegistry.from_env(model=DEFAULT_MODEL)

    with pytest.raises(ProviderConfigurationError, match="GEMINI_API_KEY"):
        registry.require_ready([ProviderCapability.CHAT])


def test_provider_registry_accepts_configured_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    registry = ProviderRegistry.from_env(model=DEFAULT_MODEL)

    settings = registry.require_ready([ProviderCapability.CHAT])

    assert settings.provider == "gemini"
    assert settings.model == DEFAULT_MODEL
    assert settings.api_key_env == "GEMINI_API_KEY"


def test_provider_registry_still_accepts_openrouter_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    registry = ProviderRegistry.from_env(model="openrouter/z-ai/glm-5.1")

    settings = registry.require_ready([ProviderCapability.CHAT])

    assert settings.provider == "openrouter"
    assert settings.api_key_env == "OPENROUTER_API_KEY"
