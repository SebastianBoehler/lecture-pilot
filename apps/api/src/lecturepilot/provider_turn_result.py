from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lecturepilot.coaching_assistance import NextCheck
from lecturepilot.models import CanvasCommand
from lecturepilot.provider_canvas_models import (
    ProviderCanvasSection,
    ProviderCanvasSectionPlacement,
)


class ProviderCanvasCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    type: Literal[
        "focus_section",
        "highlight_span",
        "open_artifact",
        "append_section",
        "update_section",
    ]
    section_id: str | None
    span_id: str | None
    highlight_text: str | None = Field(max_length=160)
    artifact_id: str | None
    section: ProviderCanvasSection | None
    placement: ProviderCanvasSectionPlacement | None

    def to_domain(self) -> CanvasCommand:
        return CanvasCommand(
            type=self.type,
            section_id=self.section_id,
            span_id=self.span_id,
            highlight_text=self.highlight_text,
            artifact_id=self.artifact_id,
            section=(self.section.to_domain() if self.section else None),
            placement=(self.placement.to_domain() if self.placement else None),
        )


class ProviderQualityGateDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    gate_id: str = Field(min_length=1, max_length=160)
    gate_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: Literal["passed", "needs_evidence"]
    reason: str = Field(min_length=1, max_length=500)
    evidence_ids: list[str] = Field(max_length=40)
    missing_evidence_ids: list[str] = Field(max_length=40)


class ProviderAgentTurnResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    message: str = Field(min_length=1)
    session_goal: str | None = Field(max_length=500)
    canvas_commands: list[ProviderCanvasCommand]
    assessment: ProviderQualityGateDecision | None
    next_check: NextCheck | None

    @model_validator(mode="after")
    def require_navigation_commands(self) -> ProviderAgentTurnResult:
        kinds = {command.type for command in self.canvas_commands}
        if not {"focus_section", "highlight_span"} <= kinds:
            raise ValueError("provider result requires focus_section and highlight_span commands")
        return self
