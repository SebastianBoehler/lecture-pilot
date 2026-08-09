from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from lecturepilot.scaffold_policy import AssistanceLevel


class NextCheckAssistance(BaseModel):
    level: AssistanceLevel = "none"
    content: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_content(self) -> "NextCheckAssistance":
        if self.level == "none" and self.content is not None:
            raise ValueError("content must be null when next-check assistance is none")
        if self.level != "none" and not (self.content and self.content.strip()):
            raise ValueError("emitted next-check assistance must include its response content")
        return self


def emitted_assistance_level(
    *,
    message: str,
    next_prompt: str | None,
    assistance: NextCheckAssistance,
) -> AssistanceLevel:
    if assistance.level == "none":
        return "none"
    content = (assistance.content or "").strip()
    prompt = (next_prompt or "").strip()
    content_at = message.find(content)
    prompt_at = message.find(prompt) if prompt else -1
    if content_at < 0:
        raise ValueError("declared next-check assistance is not present in the tutor message")
    if prompt_at < 0:
        raise ValueError("the next check is not present in the tutor message")
    if content_at + len(content) > prompt_at:
        raise ValueError("next-check assistance must appear before the next check")
    return assistance.level


def next_check_assistance_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "level": {
                "type": "string",
                "enum": ["none", "prompt", "cue", "faded_example", "worked_step"],
                "description": "Support actually emitted in message before the next check.",
            },
            "content": {
                "type": ["string", "null"],
                "description": "Exact emitted support text, or null when level is none.",
            },
        },
        "required": ["level", "content"],
    }
