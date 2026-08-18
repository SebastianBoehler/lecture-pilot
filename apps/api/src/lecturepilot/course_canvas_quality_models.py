from pydantic import BaseModel, ConfigDict, Field


class CanvasQualityIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1, max_length=120)
    block_id: str | None = Field(default=None, max_length=120)
    reason: str = Field(min_length=1)


class CanvasQualityPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issues: list[CanvasQualityIssue] = Field(max_length=30)
