from __future__ import annotations

import os
from dataclasses import dataclass

from lecturepilot.models import ProviderCapability, ProviderSettings


class ProviderConfigurationError(RuntimeError):
    """Raised when the configured model cannot satisfy the harness contract."""


_PROVIDER_KEYS = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "google": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

_DEFAULT_CAPABILITIES = {
    ProviderCapability.CHAT,
    ProviderCapability.TOOL_CALLS,
    ProviderCapability.STRUCTURED_JSON,
}

DEFAULT_MODEL = "gemini/gemini-3.1-flash-lite"


@dataclass(frozen=True)
class ProviderRegistry:
    model: str

    @classmethod
    def from_env(cls, model: str | None = None) -> "ProviderRegistry":
        configured = model or os.getenv("LECTUREPILOT_MODEL") or DEFAULT_MODEL
        return cls(model=configured)

    @property
    def provider(self) -> str:
        if "/" not in self.model:
            raise ProviderConfigurationError("Model must include a provider prefix.")
        return self.model.split("/", 1)[0].lower()

    def require_ready(self, required: list[ProviderCapability]) -> ProviderSettings:
        key_env = _PROVIDER_KEYS.get(self.provider)
        if not key_env:
            raise ProviderConfigurationError(f"Unsupported provider prefix: {self.provider}")
        missing = [capability for capability in required if capability not in _DEFAULT_CAPABILITIES]
        if missing:
            names = ", ".join(item.value for item in missing)
            raise ProviderConfigurationError(f"Model {self.model} lacks required capabilities: {names}")
        if not os.getenv(key_env):
            raise ProviderConfigurationError(f"{key_env} is required for model {self.model}.")
        return ProviderSettings(
            provider=self.provider,
            model=self.model,
            api_key_env=key_env,
            capabilities=set(_DEFAULT_CAPABILITIES),
        )
