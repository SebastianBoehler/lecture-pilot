from lecturepilot.harness import LecturePilotHarness
from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
    AttendanceStatus,
    CanvasCommand,
    CanvasState,
    ProviderCapability,
    ProviderSettings,
)
from lecturepilot.providers import ProviderRegistry


async def test_harness_uses_model_client_for_agent_turn(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    harness = LecturePilotHarness(
        provider_registry=ProviderRegistry.from_env(model="openrouter/z-ai/glm-5.1"),
        model_client=_FakeModelClient(),
    )

    result = await harness.run_turn(
        AgentTurnInput(
            user_id="u1",
            course_id="martius-ml",
            lecture_id="lecture-03",
            attendance=AttendanceStatus.PRESENT,
            message="what is your name?",
            canvas_state=CanvasState(focused_section_id="bayes-formula"),
        )
    )

    assert result.message == "My name is LecturePilot."
    assert result.canvas_commands == [
        CanvasCommand(type="focus_section", section_id="bayes-formula")
    ]
    assert result.model == "openrouter/z-ai/glm-5.1"


class _FakeModelClient:
    async def complete_turn(
        self,
        *,
        settings: ProviderSettings,
        turn: AgentTurnInput,
    ) -> AgentTurnResult:
        assert settings.capabilities >= {
            ProviderCapability.CHAT,
            ProviderCapability.STRUCTURED_JSON,
        }
        assert turn.message == "what is your name?"
        return AgentTurnResult(
            message="My name is LecturePilot.",
            canvas_commands=[CanvasCommand(type="focus_section", section_id="bayes-formula")],
            model=settings.model,
        )
