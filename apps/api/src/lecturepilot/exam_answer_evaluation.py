from __future__ import annotations

import json
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_request_options import completion_options
from lecturepilot.model_usage import ModelUsageRecorder, complete_with_usage
from lecturepilot.models import ProviderCapability, ProviderSettings
from lecturepilot.providers import ProviderConfigurationError, ProviderRegistry


class OpenAnswerEvaluationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1, max_length=220)
    prompt: str = Field(min_length=1, max_length=4000)
    answer: str = Field(min_length=1, max_length=4000)
    rubric: list[str] = Field(min_length=1, max_length=20)


class OpenAnswerEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    score: float = Field(ge=0.0, le=1.0)
    feedback: str = Field(min_length=1, max_length=600)


class OpenAnswerEvaluationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluations: list[OpenAnswerEvaluation]


class OpenAnswerEvaluationModelClient(Protocol):
    async def complete_evaluations(
        self, *, settings: ProviderSettings, items: list[OpenAnswerEvaluationInput]
    ) -> dict[str, Any]:
        """Return one rubric-grounded evaluation per submitted open answer."""


class LiteLLMOpenAnswerEvaluationClient:
    def __init__(self, usage_recorder: ModelUsageRecorder | None = None) -> None:
        self.usage_recorder = usage_recorder

    async def complete_evaluations(
        self, *, settings: ProviderSettings, items: list[OpenAnswerEvaluationInput]
    ) -> dict[str, Any]:
        try:
            from litellm import acompletion
        except ImportError as exc:
            raise ProviderConfigurationError(
                'litellm is not installed. Install the backend with the "agent" extra.'
            ) from exc
        try:
            response = await complete_with_usage(
                self.usage_recorder,
                acompletion,
                model=settings.model,
                messages=_evaluation_messages(items),
                response_format=open_answer_evaluation_response_format(),
                **completion_options(settings, temperature=0.1, reasoning_effort="low"),
            )
            return json.loads(response.choices[0].message.content)
        except (ProviderConfigurationError, ModelExecutionError):
            raise
        except Exception as exc:
            raise ModelExecutionError("Open-answer evaluation model request failed.") from exc


class OpenAnswerEvaluator:
    def __init__(
        self,
        provider_registry: ProviderRegistry | None = None,
        model_client: OpenAnswerEvaluationModelClient | None = None,
    ) -> None:
        self.provider_registry = provider_registry or ProviderRegistry.from_env()
        self.model_client = model_client or LiteLLMOpenAnswerEvaluationClient()

    async def evaluate(
        self,
        *,
        items: list[OpenAnswerEvaluationInput],
        settings: ProviderSettings | None = None,
    ) -> list[OpenAnswerEvaluation]:
        if not items:
            return []
        active_settings = settings or self.provider_registry.require_ready(
            [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
        )
        payload = await self.model_client.complete_evaluations(
            settings=active_settings,
            items=items,
        )
        evaluations = OpenAnswerEvaluationPayload.model_validate(payload).evaluations
        submitted_ids = {item.question_id for item in items}
        returned_ids = [evaluation.question_id for evaluation in evaluations]
        if len(returned_ids) != len(set(returned_ids)) or set(returned_ids) != submitted_ids:
            raise ProviderConfigurationError(
                "Open-answer evaluation ids must match submitted open-question ids."
            )
        return evaluations


def open_answer_evaluation_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "lecturepilot_open_answer_evaluation",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "evaluations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "question_id": {"type": "string"},
                                "score": {"type": "number", "minimum": 0, "maximum": 1},
                                "feedback": {"type": "string"},
                            },
                            "required": ["question_id", "score", "feedback"],
                        },
                    }
                },
                "required": ["evaluations"],
            },
        },
    }


def _evaluation_messages(items: list[OpenAnswerEvaluationInput]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You grade university exam open answers against only the supplied rubric. "
                "Return one evaluation for every submitted question. Score from 0.0 to 1.0. "
                "Feedback must identify the most useful next improvement without revealing a full answer."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {"items": [item.model_dump() for item in items]}, ensure_ascii=False
            ),
        },
    ]
