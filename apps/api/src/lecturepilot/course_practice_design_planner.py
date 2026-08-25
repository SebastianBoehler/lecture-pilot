from __future__ import annotations

from collections.abc import Sequence

from pydantic import ValidationError

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_practice_design_client import (
    LiteLLMPracticeDesignClient,
    PracticeDesignModelClient,
)
from lecturepilot.course_practice_design_models import PracticeDesignProposal
from lecturepilot.course_practice_design_prompt import practice_design_messages
from lecturepilot.course_practice_design_validation import (
    PracticeDesignValidationError,
    validate_practice_design,
)
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import ProviderCapability
from lecturepilot.providers import ProviderRegistry


class PracticeDesignPlanner:
    def __init__(
        self,
        provider_registry: ProviderRegistry | None = None,
        model_client: PracticeDesignModelClient | None = None,
    ) -> None:
        self.provider_registry = provider_registry or ProviderRegistry.from_env()
        self.model_client = model_client or LiteLLMPracticeDesignClient()

    async def propose(
        self,
        *,
        source: CanvasDocument,
        source_revision: str,
        allowed_source_paths: Sequence[str],
    ) -> PracticeDesignProposal:
        settings = self.provider_registry.require_ready(
            [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
        )
        try:
            proposal = PracticeDesignProposal.model_validate(
                await self.model_client.complete_proposal(
                    settings=settings,
                    messages=practice_design_messages(
                        source,
                        source_revision=source_revision,
                        allowed_source_paths=allowed_source_paths,
                    ),
                )
            )
            validate_practice_design(proposal, allowed_source_paths)
        except (ValidationError, PracticeDesignValidationError) as exc:
            raise ModelExecutionError(
                f"Practice-design proposal violated its contract: {exc}"
            ) from exc
        return proposal
