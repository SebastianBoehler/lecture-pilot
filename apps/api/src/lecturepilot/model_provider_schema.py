from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from lecturepilot.providers import ProviderConfigurationError


def strict_pydantic_response_format(*, name: str, model: type[BaseModel]) -> dict[str, Any]:
    """Build a provider response format from the authoritative Pydantic model."""
    try:
        from openai.lib._pydantic import to_strict_json_schema
    except ImportError as exc:
        raise ProviderConfigurationError(
            'openai is not installed. Install the backend with the "agent" extra.'
        ) from exc
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": to_strict_json_schema(model),
        },
    }
