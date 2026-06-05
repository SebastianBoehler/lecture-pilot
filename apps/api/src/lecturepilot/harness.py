from __future__ import annotations

from lecturepilot.models import AgentTurnInput, AgentTurnResult, CanvasCommand, ProviderCapability
from lecturepilot.providers import ProviderRegistry


class LecturePilotHarness:
    """Provider-agnostic agent harness contract.

    The first implementation validates provider readiness and returns a deterministic
    preview turn. Real ADK/LiteLLM execution plugs in behind this same contract.
    """

    def __init__(self, provider_registry: ProviderRegistry | None = None) -> None:
        self.provider_registry = provider_registry or ProviderRegistry.from_env()

    async def run_turn(self, turn: AgentTurnInput) -> AgentTurnResult:
        settings = self.provider_registry.require_ready([ProviderCapability.CHAT])
        section_id = turn.canvas_state.focused_section_id or "lesson-open"
        return AgentTurnResult(
            message=(
                "Provider is configured. The next implementation step routes this "
                "turn through ADK/LiteLLM and emits source-grounded canvas commands."
            ),
            canvas_commands=[CanvasCommand(type="focus_section", section_id=section_id)],
            model=settings.model,
        )

