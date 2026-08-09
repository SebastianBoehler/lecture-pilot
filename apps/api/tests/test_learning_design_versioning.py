from pathlib import Path

from auth_helpers import professor_headers
from test_learning_design_review_routes import (
    _client_with_draft,
    _review_path,
    _update_payload,
)


def test_put_and_approve_reject_a_stale_learning_map_revision(tmp_path: Path) -> None:
    client = _client_with_draft(tmp_path)
    path = _review_path()
    initial = client.get(path, headers=professor_headers()).json()
    changed = client.put(
        path,
        headers=professor_headers(),
        json={**_update_payload(initial), "objective": "Changed objective."},
    )
    assert changed.status_code == 200

    stale_update = client.put(
        path,
        headers=professor_headers(),
        json=_update_payload(initial),
    )
    stale_approval = client.post(
        f"{path}/approve",
        headers=professor_headers(),
        json={
            "draft_digest": initial["draft_digest"],
            "source_revision": initial["source_revision"],
            "learning_map_revision": initial["learning_map"]["revision"],
            "report_revision": initial["report"]["report_revision"],
            "acknowledged_warning_ids": [item["id"] for item in initial["report"]["diagnostics"]],
        },
    )

    assert stale_update.status_code == 409
    assert stale_approval.status_code == 409
