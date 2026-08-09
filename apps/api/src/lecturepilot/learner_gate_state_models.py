from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from lecturepilot.quality_gate_models import QualityGateDecision


class LearnerGateStorePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1]
    course_id: str = Field(min_length=1, max_length=120)
    lecture_id: str = Field(min_length=1, max_length=120)
    updated_at: AwareDatetime
    gates: dict[str, QualityGateDecision]

    @model_validator(mode="after")
    def validate_gate_keys(self) -> LearnerGateStorePayload:
        if any(key != decision.gate_id for key, decision in self.gates.items()):
            raise ValueError("Gate-state key does not match its decision.")
        return self

    @classmethod
    def empty(
        cls, *, course_id: str, lecture_id: str, updated_at: datetime
    ) -> LearnerGateStorePayload:
        return cls(
            schema_version=1,
            course_id=course_id,
            lecture_id=lecture_id,
            updated_at=updated_at,
            gates={},
        )
