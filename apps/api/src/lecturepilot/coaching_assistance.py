from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lecturepilot.coaching_contract import MAX_APPROVED_TASK_LENGTH, AssistanceLevel


class NextCheckAssistance(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    level: AssistanceLevel
    content: str | None = Field(max_length=2_000)

    @model_validator(mode="after")
    def validate_content(self) -> "NextCheckAssistance":
        if self.level == "none" and self.content is not None:
            raise ValueError("content must be null when next-check assistance is none")
        if self.level != "none" and not (self.content and self.content.strip()):
            raise ValueError("assisted next checks must include exact approved support content")
        return self


class NextCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    gate_id: str = Field(min_length=1, max_length=160)
    gate_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    prompt: str = Field(min_length=1, max_length=MAX_APPROVED_TASK_LENGTH)
    assistance: NextCheckAssistance


def next_check_assistance_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "level": {
                "type": "string",
                "enum": ["none", "prompt", "cue", "faded_example", "worked_step"],
                "description": "Exact server-selected assistance level for the next check.",
            },
            "content": {
                "type": ["string", "null"],
                "description": "Exact approved support text, or null when level is none.",
            },
        },
        "required": ["level", "content"],
    }
