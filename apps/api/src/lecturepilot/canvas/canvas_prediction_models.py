from pydantic import BaseModel, ConfigDict, Field


class CanvasPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    section_id: str
    block_digest: str
    publication_version: int
    question: str
    answer: str | None = Field(default=None, min_length=1, max_length=2000)
    created_at: str
