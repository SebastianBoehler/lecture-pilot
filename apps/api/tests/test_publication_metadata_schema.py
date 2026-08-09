from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lecturepilot.course_canvas_publication import CanvasPublicationMetadata


def _metadata_payload() -> dict:
    return {
        "schema_version": 1,
        "course_id": "course-1",
        "lecture_id": "lecture-1",
        "version": 1,
        "source_revision": "a" * 64,
        "draft_digest": "b" * 64,
        "learning_map_revision": "c" * 64,
        "published_at": datetime.now(UTC),
        "published_by": "professor",
    }


@pytest.mark.parametrize("value", [True, False, 1.0, "1"])
def test_publication_schema_version_requires_exact_integer_one(value: object) -> None:
    with pytest.raises(ValidationError):
        CanvasPublicationMetadata.model_validate({**_metadata_payload(), "schema_version": value})


def test_publication_metadata_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        CanvasPublicationMetadata.model_validate({**_metadata_payload(), "unexpected": True})
