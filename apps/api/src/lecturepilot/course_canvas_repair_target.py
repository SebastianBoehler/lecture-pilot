from __future__ import annotations

from pydantic import BaseModel, Field

from lecturepilot.canvas_models import CanvasDocument


class CanvasGenerationRepairTarget(BaseModel):
    """Quarantined generated content and exact coordinates for a safe AI patch."""

    candidate: CanvasDocument
    section_id: str = Field(min_length=1, max_length=120)
    block_id: str | None = Field(default=None, max_length=120)
    source_revision: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
