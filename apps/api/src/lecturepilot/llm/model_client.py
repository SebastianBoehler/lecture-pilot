from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from lecturepilot.tutor.agent_tool_executor import AgentToolExecutor
from lecturepilot.tutor.agent_tool_schemas import AgentToolProfile, tutor_tool_profile_for_message
from lecturepilot.tutor.model_commands import checkpoint_assessment_required
from lecturepilot.llm.model_usage import ModelUsageRecorder
from lecturepilot.learner.checkpoint_assessment_prompt import assessment_messages
from lecturepilot.core.models import (
    AgentTurnInput,
    AgentTurnResult,
    ProviderSettings,
)
from lecturepilot.core.observability import Observability
from lecturepilot.tutor.tutor_prompt import tutor_messages


class ModelExecutionError(RuntimeError):
    """Raised when the configured model provider rejects or fails a request."""


class ModelClient(Protocol):
    async def complete_turn(
        self,
        *,
        settings: ProviderSettings,
        turn: AgentTurnInput,
        tool_executor: AgentToolExecutor | None = None,
        observability: Observability | None = None,
        emit: Callable[[str], None] | None = None,
        tool_profile: AgentToolProfile | None = None,
    ) -> AgentTurnResult:
        """Complete one tutor turn."""


class NativeModelClient:
    def __init__(self, usage_recorder: ModelUsageRecorder | None = None, *, model=None) -> None:
        self.usage_recorder, self.model = usage_recorder, model

    async def complete_turn(
        self,
        *,
        settings: ProviderSettings,
        turn: AgentTurnInput,
        tool_executor: AgentToolExecutor | None = None,
        observability: Observability | None = None,
        emit: Callable[[str], None] | None = None,
        tool_profile: AgentToolProfile | None = None,
    ) -> AgentTurnResult:
        from lecturepilot.tutor.native_tutor import native_tutor_turn

        assessment = checkpoint_assessment_required(turn)
        return await native_tutor_turn(
            settings=settings,
            turn=turn,
            messages=assessment_messages(turn) if assessment else tutor_messages(turn),
            usage_recorder=self.usage_recorder,
            model=self.model,
            tool_executor=None if assessment else tool_executor,
            observability=observability or Observability(),
            emit=emit,
            tool_profile=tool_profile or tutor_tool_profile_for_message(turn.message),
        )
