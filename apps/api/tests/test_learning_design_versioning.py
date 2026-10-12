from pathlib import Path

from auth_helpers import approval_input, professor_headers
from test_learning_design_review_routes import (
    _client_with_draft,
    _publish_path,
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
        json={
            **_update_payload(initial),
            "prerequisites": [
                {"section_id": "intro", "prerequisite_ids": []},
                {"section_id": "practice", "prerequisite_ids": []},
            ],
        },
    )
    assert changed.status_code == 200

    stale_update = client.put(
        path,
        headers=professor_headers(),
        json=_update_payload(initial),
    )
    stale_approval = client.post(
        _publish_path(), headers=professor_headers(), json=approval_input(initial)
    )

    assert stale_update.status_code == 409
    assert stale_approval.status_code == 409
