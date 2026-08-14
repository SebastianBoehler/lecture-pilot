import pytest

from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_quality import (
    CanvasQualityReviewer,
    canvas_quality_response_format,
)
from lecturepilot.model_client import ModelExecutionError
from test_course_canvas_quality import _QualityClient, _settings, _source_document


def test_quality_review_schema_constrains_issue_coordinates_to_candidate() -> None:
    schema = canvas_quality_response_format(_source_document())
    issue_properties = schema["json_schema"]["schema"]["properties"]["issues"]["items"][
        "properties"
    ]

    assert issue_properties["section_id"]["enum"] == ["topic"]
    assert issue_properties["block_id"]["enum"] == [None, "source", "quiz"]


async def test_quality_reviewer_rejects_unknown_issue_coordinates() -> None:
    document = _source_document()
    reviewer = CanvasQualityReviewer(
        model_client=_QualityClient(
            [
                {
                    "section_id": "missing-section",
                    "block_id": None,
                    "reason": "Unsupported claim.",
                }
            ]
        )
    )

    with pytest.raises(ModelExecutionError, match="unknown section"):
        await reviewer.validate(
            settings=_settings(),
            source_document=document,
            candidate_document=document,
        )


async def test_quality_reviewer_maps_mirrored_source_section_to_candidate() -> None:
    source = _source_document()
    candidate_section = source.sections[0].model_copy(update={"id": "learning-1-topic"})
    candidate = source.model_copy(update={"sections": [candidate_section]})
    reviewer = CanvasQualityReviewer(
        model_client=_QualityClient(
            [
                {
                    "section_id": "topic",
                    "block_id": None,
                    "reason": "The section contains an unsupported teaching claim.",
                }
            ]
        )
    )

    with pytest.raises(CanvasGenerationRepairableError) as caught:
        await reviewer.validate(
            settings=_settings(),
            source_document=source,
            candidate_document=candidate,
        )

    assert caught.value.section_id == "learning-1-topic"
    assert caught.value.block_id is None


async def test_quality_reviewer_falls_back_to_valid_section_for_unknown_block() -> None:
    document = _source_document()
    reviewer = CanvasQualityReviewer(
        model_client=_QualityClient(
            [
                {
                    "section_id": "topic",
                    "block_id": "topic-checkpoint-that-does-not-exist",
                    "reason": "The assessment answer is unsupported.",
                }
            ]
        )
    )

    with pytest.raises(CanvasGenerationRepairableError) as caught:
        await reviewer.validate(
            settings=_settings(),
            source_document=document,
            candidate_document=document,
        )

    assert caught.value.section_id == "topic"
    assert caught.value.block_id is None
    assert "assessment answer is unsupported" in str(caught.value)
