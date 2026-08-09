from pathlib import Path

from auth_helpers import professor_headers
from test_learning_design_review_routes import (
    _client_with_draft,
    _document,
    _publish_path,
    _review_path,
    _source_revision,
    _write_source_manifest,
)


def test_regeneration_and_source_change_invalidate_approval(tmp_path: Path) -> None:
    client = _client_with_draft(tmp_path)
    review = client.get(_review_path(), headers=professor_headers()).json()
    approved = client.post(
        f"{_review_path()}/approve",
        headers=professor_headers(),
        json={
            "draft_digest": review["draft_digest"],
            "source_revision": review["source_revision"],
            "learning_map_revision": review["learning_map"]["revision"],
        },
    )
    assert approved.status_code == 200

    workspace = client.app.state.canvas_workspace
    workspace.write_course_canvas_draft(
        _document(title="Regenerated draft"),
        expected_source_revision=_source_revision(workspace),
    )
    regenerated = client.get(_review_path(), headers=professor_headers())
    blocked = client.post(_publish_path(), headers=professor_headers())
    assert regenerated.status_code == 200
    assert regenerated.json()["approval"] is None
    assert regenerated.json()["draft_digest"] != review["draft_digest"]
    assert blocked.status_code == 409

    current = regenerated.json()
    approved_again = client.post(
        f"{_review_path()}/approve",
        headers=professor_headers(),
        json={
            "draft_digest": current["draft_digest"],
            "source_revision": current["source_revision"],
            "learning_map_revision": current["learning_map"]["revision"],
        },
    )
    assert approved_again.status_code == 200
    _write_source_manifest(workspace, source_sha="b" * 64)
    assert client.post(_publish_path(), headers=professor_headers()).status_code == 409
