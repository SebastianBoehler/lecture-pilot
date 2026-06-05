from __future__ import annotations

from lecturepilot.guided_tutor import LOCAL_PREVIEW_USER_ID, run_local_preview_turn
from lecturepilot.model_client import LiteLLMModelClient, ModelClient
from lecturepilot.models import AgentTurnInput, AgentTurnResult, ProviderCapability
from lecturepilot.providers import ProviderRegistry


class LecturePilotHarness:
    """Provider-agnostic agent harness contract."""

    def __init__(
        self,
        provider_registry: ProviderRegistry | None = None,
        model_client: ModelClient | None = None,
    ) -> None:
        self.provider_registry = provider_registry or ProviderRegistry.from_env()
        self.model_client = model_client or LiteLLMModelClient()

    async def run_turn(self, turn: AgentTurnInput) -> AgentTurnResult:
        if turn.user_id == LOCAL_PREVIEW_USER_ID:
            return run_local_preview_turn(turn)

        settings = self.provider_registry.require_ready(
            [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
        )
        return await self.model_client.complete_turn(settings=settings, turn=turn)
