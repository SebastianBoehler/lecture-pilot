from pydantic import BaseModel, ConfigDict, Field


class CriterionQuote(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    evidence_id: str = Field(min_length=1, max_length=160)
    quote: str = Field(min_length=1, max_length=500)
