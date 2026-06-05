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
        if self._contains_any(normalized, ("test", "quiz", "check", "understood", "skill")):
            return "skill-check"
        if self._contains_any(normalized, ("goal", "learn", "purpose", "objective")):
            return "learning-goals"
        if self._contains_any(normalized, ("mistake", "wrong", "failure", "misconception")):
            return "failure-mode"
        if "kernel" in normalized:
            return "kernel-trick"
        if "feature" in normalized or "map" in normalized:
            return "feature-maps"
        return turn.canvas_state.focused_section_id or "feature-maps"

    def _preview_message(self, turn: AgentTurnInput, section_id: str) -> str:
        if section_id == "learning-goals":
            return (
                "Focus moved to the learning goals. The purpose of this lecture is to connect "
                "feature maps, inner products, and kernels into one usable modeling decision."
            )
        if section_id == "skill-check":
            return (
                "Focus moved to the skill check. Answer this before we continue: what does "
                "k(x, x') replace, and why does that matter computationally?"
            )
        if section_id == "failure-mode":
            return (
                "Focus moved to the common failure mode. Kernels do not make the problem easy "
                "by magic; they preserve a specific inner-product computation in feature space."
            )
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

    def _contains_any(self, text: str, needles: tuple[str, ...]) -> bool:
        return any(needle in text for needle in needles)
