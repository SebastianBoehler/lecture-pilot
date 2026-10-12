from reviewed_task_bank_helpers import with_bank
import json
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelResponse, TextPart

import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_practice_design_review_models import REVIEW_DIMENSIONS
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import ProviderCapability, ProviderSettings
from practice_design_test_helpers import proposal


SOURCE_REVISION = "a" * 64


@pytest.mark.asyncio
async def test_native_review_client_uses_a_strict_dimension_complete_schema() -> None:
    from lecturepilot.course_practice_design_review_client import (
        NativePracticeDesignReviewClient,
    )

    calls: list[dict] = []

    def fake_completion(messages, info):
        calls.append(info.model_request_parameters)
        return ModelResponse(parts=[TextPart(_review_payload_json())])

    client = NativePracticeDesignReviewClient(model=FunctionModel(fake_completion))

    payload = await client.complete_review(
        settings=_settings(),
        source=_source(),
        proposal=proposal(),
        messages=[
            {"role": "system", "content": "Review the supplied plan."},
            {"role": "user", "content": "review"},
        ],
        allowed_source_paths=("lecture-01.md",),
        catalogue={"e0": {"source_path": "lecture-01.md", "excerpt": "evidence"}},
    )

    assert len(payload["checks"]) == len(REVIEW_DIMENSIONS)
    request = calls[0]
    assert request.output_mode == "native"
    assert request.output_object.strict is True
    check_schema = request.output_object.json_schema["properties"]["checks"]["items"]
    assert set(check_schema["required"]) == set(check_schema["properties"])
    dimension_schema = check_schema["properties"]["dimension"]
    assert tuple(dimension_schema["enum"]) == REVIEW_DIMENSIONS
    assert check_schema["properties"]["supporting_anchors"]["items"]["enum"] == ["e0"]


@pytest.mark.asyncio
async def test_review_provider_failure_is_returned_without_a_reviewed_proposal() -> None:
    from lecturepilot.course_practice_design_planner import PracticeDesignPlanner

    planner = PracticeDesignPlanner(
        provider_registry=_Registry(),
        review_client=_FailingReviewClient(),
    )

    with pytest.raises(ModelExecutionError, match="critic unavailable"):
        await planner.review(
            source=_source(),
            source_revision=SOURCE_REVISION,
            allowed_source_paths=("lecture-01.md",),
            proposal=_banked_proposal(),
        )


@pytest.mark.asyncio
async def test_critic_issue_support_must_quote_the_exact_routed_source() -> None:
    from lecturepilot.course_practice_design_planner import PracticeDesignPlanner

    payload = _review_payload()
    payload["checks"][0].update(
        {
            "severity": "warning",
            "target_ids": ["derive-conclusion"],
            "supporting_anchors": [
                {
                    "source_path": "lecture-01.md",
                    "excerpt": "This unrelated wording is absent.",
                }
            ],
        }
    )
    planner = PracticeDesignPlanner(
        provider_registry=_Registry(),
        review_client=_StaticReviewClient(payload),
    )

    with pytest.raises(ModelExecutionError, match="verbatim excerpt"):
        await planner.review(
            source=_source(),
            source_revision=SOURCE_REVISION,
            allowed_source_paths=("lecture-01.md",),
            proposal=_banked_proposal(),
        )


def _banked_proposal():
    draft = proposal()
    return draft.model_copy(update={"targets": tuple(with_bank(t) for t in draft.targets)})


class _FailingReviewClient:
    async def complete_review(self, **_kwargs) -> dict:
        raise ModelExecutionError("critic unavailable")


class _StaticReviewClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    async def complete_review(self, **_kwargs) -> dict:
        return self.payload


class _Registry:
    def require_ready(self, _required):
        return _settings()


def _settings() -> ProviderSettings:
    return ProviderSettings(
        provider="openai",
        model="openai/gpt-5.6-luna",
        api_key_env="OPENAI_API_KEY",
        capabilities={ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON},
    )


def _review_payload() -> dict:
    return {
        "checks": [
            {
                "dimension": dimension,
                "severity": "pass",
                "summary": f"No material {dimension} issue found.",
                "target_ids": [],
                "supporting_anchors": [],
            }
            for dimension in REVIEW_DIMENSIONS
        ]
    }


def _review_payload_json() -> str:

    return json.dumps(_review_payload())


def _source() -> CanvasDocument:
    return CanvasDocument(
        id="course-01-lecture-01",
        course_id="course-01",
        lecture_id="lecture-01",
        title="Practice design",
        source_kind="markdown",
        source_ref="lecture-01.md",
        workspace_path="source.json",
        sections=[
            CanvasSection(
                id="evidence",
                title="Evidence",
                source_ref="lecture-01.md",
                blocks=[
                    CanvasBlock(
                        id="evidence-block",
                        type="paragraph",
                        text="Use the evidence to derive and justify a conclusion.",
                    )
                ],
            )
        ],
    )
