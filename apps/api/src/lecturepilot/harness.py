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
        section_id = self._target_section(turn)
        return AgentTurnResult(
            message=self._preview_message(turn, section_id),
            canvas_commands=[CanvasCommand(type="focus_section", section_id=section_id)],
            model=settings.model,
        )

    def _target_section(self, turn: AgentTurnInput) -> str:
        normalized = turn.message.lower()
        if "kernel" in normalized:
            return "kernel-trick"
        if "feature" in normalized or "map" in normalized:
            return "feature-maps"
        return turn.canvas_state.focused_section_id or "feature-maps"

    def _preview_message(self, turn: AgentTurnInput, section_id: str) -> str:
        if section_id == "kernel-trick":
            return (
                "Focus moved to the kernel trick. The core point is that the algorithm "
                "can use k(x, x') as the lifted-space inner product without constructing "
                "the feature vectors explicitly."
            )
        if turn.attendance.value == "absent":
            return (
                "I will rebuild this from the lecture notes first, then check the argument "
                "with a short question before moving on."
            )
        return "I will keep the current section in focus and deepen the argument from there."
