import json
from collections.abc import Callable
from typing import Any

import pytest
from openai.lib._pydantic import to_strict_json_schema
from pydantic import BaseModel, ValidationError

from lecturepilot.course_practice_design_benchmark_evaluator import (
    practice_design_benchmark_response_format,
)
from lecturepilot.course_practice_design_benchmark_models import (
    BENCHMARK_DIMENSIONS,
    PracticeDesignBenchmarkEvaluation,
)
from lecturepilot.course_practice_design_models import PracticeDesignProposal
from lecturepilot.course_practice_design_prompt import practice_design_response_format
from lecturepilot.course_practice_design_review_models import (
    PracticeDesignReviewResult,
)
from lecturepilot.course_practice_design_review_prompt import (
    practice_design_review_response_format,
)
from practice_design_test_helpers import passing_review, proposal


ResponseFormatFactory = Callable[[], dict[str, Any]]


@pytest.mark.parametrize(
    ("response_format_factory", "name", "model"),
    (
        (
            practice_design_response_format,
            "lecturepilot_practice_design",
            PracticeDesignProposal,
        ),
        (
            practice_design_review_response_format,
            "lecturepilot_practice_design_semantic_review",
            PracticeDesignReviewResult,
        ),
        (
            practice_design_benchmark_response_format,
            "lecturepilot_practice_design_benchmark_review",
            PracticeDesignBenchmarkEvaluation,
        ),
    ),
)
def test_practice_design_response_formats_use_the_strict_production_model_schema(
    response_format_factory: ResponseFormatFactory,
    name: str,
    model: type[BaseModel],
) -> None:
    response_format = response_format_factory()

    assert response_format == {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": to_strict_json_schema(model),
        },
    }
    _assert_every_object_is_strict(response_format["json_schema"]["schema"])


def test_practice_design_strict_schema_preserves_nullable_semantic_fields() -> None:
    schema = practice_design_response_format()["json_schema"]["schema"]
    criterion = schema["$defs"]["PracticeEvidenceCriterion"]
    planning_context = schema["$defs"]["PracticePlanningContext"]

    assert _allows_null(criterion["properties"]["source_anchor"])
    for field in (
        "learner_level",
        "prerequisites",
        "time_budget_minutes",
        "allowed_aids",
        "assessment_conditions",
    ):
        assert _allows_null(planning_context["properties"][field])


@pytest.mark.parametrize(
    ("model", "payload"),
    (
        (
            PracticeDesignProposal,
            {
                **proposal().model_dump(mode="json"),
                "targets": [
                    {
                        **proposal().model_dump(mode="json")["targets"][0],
                        "review_after_days": 0,
                    }
                ],
            },
        ),
        (
            PracticeDesignReviewResult,
            {
                "checks": [
                    {
                        **passing_review().model_dump(mode="json")["checks"][0],
                        "severity": "warning",
                        "supporting_anchors": [],
                    },
                    *passing_review().model_dump(mode="json")["checks"][1:],
                ]
            },
        ),
        (
            PracticeDesignBenchmarkEvaluation,
            {
                "scores": [
                    {
                        "dimension": dimension,
                        "score": 0 if index == 0 else 5,
                        "rationale": "No material defect found.",
                        "failure_examples": [],
                    }
                    for index, dimension in enumerate(BENCHMARK_DIMENSIONS)
                ]
            },
        ),
    ),
)
def test_production_models_still_reject_invalid_provider_json(
    model: type[BaseModel], payload: dict[str, Any]
) -> None:
    provider_json = json.dumps(payload)

    with pytest.raises(ValidationError):
        model.model_validate_json(provider_json)


def _assert_every_object_is_strict(value: Any) -> None:
    if isinstance(value, dict):
        if value.get("type") == "object":
            assert value.get("additionalProperties") is False
            assert value.get("required") == list(value.get("properties", ()))
        for child in value.values():
            _assert_every_object_is_strict(child)
    elif isinstance(value, list):
        for child in value:
            _assert_every_object_is_strict(child)


def _allows_null(schema: dict[str, Any]) -> bool:
    return any(branch.get("type") == "null" for branch in schema.get("anyOf", ()))
