import pytest
from pydantic import ValidationError

from lecturepilot.course_practice_design_benchmark_models import (
    BENCHMARK_DIMENSIONS,
    SCORE_ANCHORS,
    PracticeDesignBenchmarkEvaluation,
    PracticeDesignBenchmarkReviewerJudgment,
    summarize_dimension_scores,
)


def test_benchmark_evaluation_requires_every_ordered_dimension_on_a_bounded_scale() -> None:
    evaluation = _evaluation(5)

    assert tuple(score.dimension for score in evaluation.scores) == BENCHMARK_DIMENSIONS
    assert SCORE_ANCHORS == {
        1: "Unusable: contradicted, unsupported, leaked, or not assessable.",
        2: "Major defects: substantial repair is needed before use.",
        3: "Mixed: usable elements remain, but a material weakness persists.",
        4: "Sound: no major defect, with a minor specific limitation.",
        5: "Strong: fully satisfies the dimension with no material defect found.",
    }

    payload = evaluation.model_dump(mode="json")
    payload["scores"][0]["score"] = 0
    with pytest.raises(ValidationError):
        PracticeDesignBenchmarkEvaluation.model_validate(payload)

    payload = evaluation.model_dump(mode="json")
    payload["scores"][-2:] = reversed(payload["scores"][-2:])
    with pytest.raises(ValidationError, match="every benchmark dimension"):
        PracticeDesignBenchmarkEvaluation.model_validate(payload)


def test_submaximal_score_requires_a_source_supported_failure_example() -> None:
    payload = _evaluation(5).model_dump(mode="json")
    payload["scores"][0].update({"score": 4, "failure_examples": []})

    with pytest.raises(ValidationError, match="source-supported failure example"):
        PracticeDesignBenchmarkEvaluation.model_validate(payload)


def test_dimension_summary_preserves_reviewer_scores_and_exposes_disagreement() -> None:
    first = _evaluation(5).model_dump(mode="json")
    first["scores"][0] = _score(BENCHMARK_DIMENSIONS[0], 2)
    judgments = (
        PracticeDesignBenchmarkReviewerJudgment(
            reviewer_model="openai/reviewer-a",
            evaluation=PracticeDesignBenchmarkEvaluation.model_validate(first),
        ),
        PracticeDesignBenchmarkReviewerJudgment(
            reviewer_model="gemini/reviewer-b",
            evaluation=_evaluation(5),
        ),
    )

    summary = summarize_dimension_scores(judgments)[0]

    assert summary.dimension == "source_faithfulness"
    assert tuple(item.model_dump() for item in summary.reviewer_scores) == (
        {"reviewer_model": "openai/reviewer-a", "score": 2},
        {"reviewer_model": "gemini/reviewer-b", "score": 5},
    )
    assert summary.mean_score == 3.5
    assert summary.minimum_score == 2
    assert summary.maximum_score == 5
    assert summary.score_spread == 3


def _evaluation(score: int) -> PracticeDesignBenchmarkEvaluation:
    return PracticeDesignBenchmarkEvaluation(
        scores=[_score(dimension, score) for dimension in BENCHMARK_DIMENSIONS]
    )


def _score(dimension: str, score: int) -> dict:
    examples = []
    if score < 5:
        examples = [
            {
                "description": "The proposal omits a source-supported condition.",
                "target_ids": ["target-1"],
                "supporting_anchors": [{"source_path": "fixture.md", "excerpt": "source evidence"}],
            }
        ]
    return {
        "dimension": dimension,
        "score": score,
        "rationale": "The dimension was checked against the complete source packet.",
        "failure_examples": examples,
    }
