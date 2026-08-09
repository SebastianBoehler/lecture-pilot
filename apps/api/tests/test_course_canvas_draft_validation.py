from pathlib import Path

import pytest

from auth_helpers import professor_headers
from canvas_workspace_fixtures import published_course_canvas, write_canvas_draft
from lecturepilot.canvas_models import MAX_SOURCE_REF_LENGTH, CanvasDocument
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_canvas_plan_parser import planned_document
from lecturepilot.course_canvas_store import InvalidCanvasDraftError
from test_course_canvas_draft_integrity import (
    _InvalidCoursePlanner,
    _client_contract_headers,
    _course_client,
    _revision,
)


def test_planned_source_ref_preserves_bounded_source_evidence() -> None:
    source_ref = "s" * MAX_SOURCE_REF_LENGTH
    source = published_course_canvas("demo-course", "lecture-01").model_copy(
        update={"source_kind": "markdown", "source_ref": source_ref}
    )
    result = planned_document(
        {
            "sections": [
                {
                    "id": "introduction",
                    "title": "Introduction",
                    "source_ref": source_ref,
                    "blocks": [{"type": "paragraph", "text": "Source-backed detail."}],
                }
            ]
        },
        source,
    )

    validated = CanvasDocument.model_validate(result.model_dump())
    assert validated.source_ref == source_ref
    assert len(validated.source_ref) == MAX_SOURCE_REF_LENGTH


def test_invalid_draft_does_not_replace_existing_draft(tmp_path: Path) -> None:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    existing = published_course_canvas("demo-course", "lecture-01")
    stored = write_canvas_draft(workspace, existing)
    invalid = existing.model_copy(update={"title": "Invalid replacement", "source_ref": "s" * 501})

    with pytest.raises(InvalidCanvasDraftError):
        workspace.course_canvas_store.write_draft(
            invalid, expected_source_revision=_revision(workspace, "demo-course")
        )

    preserved = workspace.course_canvas_store.read_draft(
        course_id="demo-course", lecture_id="lecture-01"
    )
    assert preserved is not None
    assert preserved.title == existing.title
    assert preserved.source_ref == stored.source_ref


def test_generation_rejects_invalid_draft_without_replacing_existing(tmp_path: Path) -> None:
    client = _course_client(tmp_path)
    existing = published_course_canvas("draft-integrity", "lecture-01")
    write_canvas_draft(client.app.state.canvas_workspace, existing)
    client.app.state.course_planner = _InvalidCoursePlanner()

    response = client.post(
        "/admin/courses/draft-integrity/lectures/lecture-01/canvas/draft",
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "draft-request-key-invalid-0001",
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Generated canvas draft is invalid and was not saved."
    preview = client.get(
        "/admin/courses/draft-integrity/lectures/lecture-01/canvas/draft",
        headers=professor_headers(),
    )
    assert preview.status_code == 200
    assert preview.json()["title"] == existing.title
