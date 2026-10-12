from pathlib import Path

import pytest

from auth_helpers import approval_input, professor_headers
from test_learning_design_review_routes import (
    _client_with_draft,
    _publish_path,
    _review_path,
    _update_payload,
)


def test_approve_and_publish_binds_the_exact_reviewed_draft(tmp_path: Path) -> None:
    client = _client_with_draft(tmp_path)
    review = client.get(_review_path(), headers=professor_headers()).json()
    assert review["report"]["diagnostics"]

    payload = approval_input(review)
    stale = client.post(
        _publish_path(),
        headers=professor_headers(),
        json={**payload, "learning_map_revision": "0" * 64},
    )
    assert stale.status_code == 409
    assert client.get(_review_path(), headers=professor_headers()).json()["approval"] is None
    published = client.post(_publish_path(), headers=professor_headers(), json=payload)
    assert published.status_code == 200, published.json()
    approval = client.get(_review_path(), headers=professor_headers()).json()["approval"]
    assert set(approval) == {
        "approved_by",
        "approved_at",
        "draft_digest",
        "source_revision",
        "practice_design_revision",
    }


def test_failed_publication_does_not_keep_the_approval(tmp_path: Path, monkeypatch) -> None:
    client = _client_with_draft(tmp_path)
    review = client.get(_review_path(), headers=professor_headers()).json()
    workspace = client.app.state.canvas_workspace

    def fail(**_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(workspace, "publish_course_canvas_draft", fail)
    with pytest.raises(OSError, match="disk full"):
        client.post(_publish_path(), headers=professor_headers(), json=approval_input(review))
    assert client.get(_review_path(), headers=professor_headers()).json() == review


def test_update_recomputes_the_report_and_publication_keeps_it_private(tmp_path: Path) -> None:
    client = _client_with_draft(tmp_path)
    initial = client.get(_review_path(), headers=professor_headers()).json()
    changed = client.put(
        _review_path(),
        headers=professor_headers(),
        json={**_update_payload(initial), "objective": "A revised exact-draft objective."},
    )
    assert changed.status_code == 409, changed.json()

    published = client.post(
        _publish_path(), headers=professor_headers(), json=approval_input(initial)
    )
    assert published.status_code == 200, published.json()
    published_dir = client.app.state.canvas_workspace.course_canvas_store.path(
        "design-course", "lecture-01"
    )
    assert not (published_dir / "learning-design.json").exists()
