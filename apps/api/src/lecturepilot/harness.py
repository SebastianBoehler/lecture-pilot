from __future__ import annotations

from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.model_client import LiteLLMModelClient, ModelClient
from lecturepilot.models import AgentTurnInput, AgentTurnResult, ProviderCapability
from lecturepilot.observability import Observability
from lecturepilot.providers import ProviderRegistry

LOCAL_PREVIEW_USER_ID = "local-preview-user"


class LecturePilotHarness:
    """Provider-agnostic agent harness contract."""

    def __init__(
        self,
        provider_registry: ProviderRegistry | None = None,
        model_client: ModelClient | None = None,
    ) -> None:
        self.provider_registry = provider_registry or ProviderRegistry.from_env()
        self.model_client = model_client or LiteLLMModelClient()

    async def run_turn(
        self,
        turn: AgentTurnInput,
        *,
        tool_executor: AgentToolExecutor | None = None,
        observability: Observability | None = None,
        emit=None,
    ) -> AgentTurnResult:
        required = [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
        if tool_executor is not None:
            required.append(ProviderCapability.TOOL_CALLS)
        provider_registry = (
            ProviderRegistry.from_env(model=turn.model) if turn.model else self.provider_registry
        )
        settings = provider_registry.require_ready(required)
        return await self.model_client.complete_turn(
            settings=settings,
            turn=turn,
            tool_executor=tool_executor,
            observability=observability,
            emit=emit,
        )
