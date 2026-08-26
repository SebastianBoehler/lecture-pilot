from types import SimpleNamespace
import json
import sys

import pytest

from lecturepilot.course_practice_design_benchmark_evaluator import (
    LiteLLMPracticeDesignBenchmarkClient,
    practice_design_benchmark_messages,
    validate_practice_design_benchmark_evaluation,
)
from lecturepilot.course_practice_design_benchmark_models import BENCHMARK_DIMENSIONS
from lecturepilot.course_practice_design_validation import PracticeDesignValidationError
from lecturepilot.models import ProviderCapability, ProviderSettings
from practice_design_review_test_helpers import passing_review, source_document
from practice_design_test_helpers import proposal


def test_evaluator_prompt_audits_the_production_proposal_and_semantic_review() -> None:
    messages = practice_design_benchmark_messages(
        source_document(text="Source evidence."),
        proposal(),
        passing_review(),
        source_revision="a" * 64,
    )

    assert "1 = Unusable" in messages[0]["content"]
    assert "source_faithfulness" in messages[0]["content"]
    assert "misconception_plausibility" in messages[0]["content"]
    assert "PRODUCTION SEMANTIC REVIEW" in messages[1]["content"]
    assert '"source_entailment"' in messages[1]["content"]
    assert "PRODUCTION PRACTICE DESIGN" in messages[1]["content"]
    assert "SOURCE EVIDENCE" in messages[1]["content"]


@pytest.mark.asyncio
async def test_native_evaluator_client_requests_the_strict_benchmark_schema(monkeypatch) -> None:
    calls: list[dict] = []

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=json.dumps(_evaluation_payload())))
            ],
            usage=None,
        )

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))

    payload = await LiteLLMPracticeDesignBenchmarkClient().complete_evaluation(
        settings=_settings(), messages=[{"role": "user", "content": "evaluate"}]
    )

    assert tuple(score["dimension"] for score in payload["scores"]) == BENCHMARK_DIMENSIONS
    request = calls[0]
    assert request["response_format"]["type"] == "json_schema"
    assert request["response_format"]["json_schema"]["strict"] is True
    score_schema = request["response_format"]["json_schema"]["schema"]["$defs"][
        "PracticeDesignBenchmarkScore"
    ]
    assert tuple(score_schema["properties"]["dimension"]["enum"]) == BENCHMARK_DIMENSIONS
    assert score_schema["properties"]["score"]["minimum"] == 1
    assert score_schema["properties"]["score"]["maximum"] == 5


def test_evaluation_failure_examples_must_reference_real_targets_and_source_text() -> None:
    payload = _evaluation_payload()
    payload["scores"][0] = {
        "dimension": BENCHMARK_DIMENSIONS[0],
        "score": 3,
        "rationale": "A material unsupported detail remains.",
        "failure_examples": [
            {
                "description": "The target claims content absent from the source.",
                "target_ids": ["unknown-target"],
                "supporting_anchors": [
                    {"source_path": "lecture-01.md", "excerpt": "absent wording"}
                ],
            }
        ],
    }

    with pytest.raises(PracticeDesignValidationError, match="unknown practice targets"):
        validate_practice_design_benchmark_evaluation(
            payload,
            proposal=proposal(),
            source=source_document(text="Source evidence."),
            allowed_source_paths=("lecture-01.md",),
        )


def _evaluation_payload() -> dict:
    return {
        "scores": [
            {
                "dimension": dimension,
                "score": 5,
                "rationale": "No material defect found against the complete packet.",
                "failure_examples": [],
            }
            for dimension in BENCHMARK_DIMENSIONS
        ]
    }


def _settings() -> ProviderSettings:
    return ProviderSettings(
        provider="openai",
        model="openai/reviewer-a",
        api_key_env="OPENAI_API_KEY",
        capabilities={ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON},
    )
