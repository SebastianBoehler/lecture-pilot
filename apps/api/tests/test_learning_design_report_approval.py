from pathlib import Path

from auth_helpers import professor_headers
from test_learning_design_review_routes import (
    _client_with_draft,
    _publish_path,
    _review_path,
    _update_payload,
)


def test_approval_requires_the_exact_report_and_diagnostic_set(tmp_path: Path) -> None:
    client = _client_with_draft(tmp_path)
    review = client.get(_review_path(), headers=professor_headers()).json()
    assert "report" in review
    warning_ids = [item["id"] for item in review["report"]["diagnostics"]]
    assert warning_ids

    payload = _approval_payload(review, warning_ids)
    responses = [
        client.post(
            f"{_review_path()}/approve",
            headers=professor_headers(),
            json={**payload, "report_revision": "0" * 64},
        ),
        client.post(
            f"{_review_path()}/approve",
            headers=professor_headers(),
            json={**payload, "acknowledged_warning_ids": warning_ids[:-1]},
        ),
        client.post(
            f"{_review_path()}/approve",
            headers=professor_headers(),
            json={**payload, "acknowledged_warning_ids": [*warning_ids, "unknown-warning"]},
        ),
        client.post(
            f"{_review_path()}/approve",
            headers=professor_headers(),
            json={**payload, "acknowledged_warning_ids": [*warning_ids, warning_ids[0]]},
        ),
    ]

    assert [response.status_code for response in responses] == [409, 409, 409, 409]
    approved = client.post(
        f"{_review_path()}/approve",
        headers=professor_headers(),
        json=payload,
    )
    assert approved.status_code == 200, approved.json()
    approval = approved.json()["approval"]
    assert approval["report_revision"] == review["report"]["report_revision"]
    assert approval["acknowledged_warning_ids"] == warning_ids


def test_update_recomputes_the_report_and_publication_keeps_it_private(tmp_path: Path) -> None:
    client = _client_with_draft(tmp_path)
    initial = client.get(_review_path(), headers=professor_headers()).json()
    assert "report" in initial
    changed = client.put(
        _review_path(),
        headers=professor_headers(),
        json={**_update_payload(initial), "objective": "A revised exact-draft objective."},
    )
    assert changed.status_code == 200, changed.json()
    current = changed.json()
    assert current["approval"] is None
    assert current["report"]["draft_digest"] == current["draft_digest"]
    assert current["report"]["source_revision"] == current["source_revision"]
    assert current["report"]["learning_map_revision"] == current["learning_map"]["revision"]
    assert current["report"]["report_revision"] != initial["report"]["report_revision"]

    warning_ids = [item["id"] for item in current["report"]["diagnostics"]]
    approved = client.post(
        f"{_review_path()}/approve",
        headers=professor_headers(),
        json=_approval_payload(current, warning_ids),
    )
    assert approved.status_code == 200, approved.json()
    published = client.post(_publish_path(), headers=professor_headers())
    assert published.status_code == 200, published.json()
    published_dir = client.app.state.canvas_workspace.course_canvas_store.path(
        "design-course", "lecture-01"
    )
    assert not (published_dir / "learning-design.json").exists()


def _approval_payload(review: dict, warning_ids: list[str]) -> dict:
    return {
        "draft_digest": review["draft_digest"],
        "source_revision": review["source_revision"],
        "learning_map_revision": review["learning_map"]["revision"],
        "report_revision": review["report"]["report_revision"],
        "acknowledged_warning_ids": warning_ids,
    }
