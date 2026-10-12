from pathlib import Path

from auth_helpers import approval_input, professor_headers
from lecturepilot.learning_design.course_practice_design_store import PracticeDesignStore
from test_learning_design_review_routes import (
    _client_with_draft,
    _publish_path,
    _review_path,
    _source_revision,
    _write_source_manifest,
)


def test_regeneration_and_source_change_invalidate_approval(tmp_path: Path) -> None:
    client = _client_with_draft(tmp_path)
    review = client.get(_review_path(), headers=professor_headers()).json()
    approved = client.post(
        _publish_path(), headers=professor_headers(), json=approval_input(review)
    )
    assert approved.status_code == 200

    workspace = client.app.state.canvas_workspace
    revision = _source_revision(workspace)
    design = PracticeDesignStore(workspace.layout).require_approved(
        course_id="design-course", lecture_id="lecture-01", source_revision=revision
    )
    workspace.write_course_canvas_draft(
        workspace.read_course_canvas_draft(
            course_id="design-course", lecture_id="lecture-01"
        ).model_copy(update={"title": "Regenerated draft"}),
        expected_source_revision=revision,
        practice_design=design,
    )
    regenerated = client.get(_review_path(), headers=professor_headers())
    blocked = client.post(_publish_path(), headers=professor_headers(), json=approval_input(review))
    assert regenerated.status_code == 200
    assert regenerated.json()["approval"] is None
    assert regenerated.json()["draft_digest"] != review["draft_digest"]
    assert blocked.status_code == 409

    current = regenerated.json()
    _write_source_manifest(workspace, source_sha="b" * 64)
    stale_source = client.post(
        _publish_path(), headers=professor_headers(), json=approval_input(current)
    )
    assert stale_source.status_code in {404, 409}
    assert client.get(_review_path(), headers=professor_headers()).status_code in {404, 409}
