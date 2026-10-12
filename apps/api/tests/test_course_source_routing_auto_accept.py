from pathlib import Path

from auth_helpers import professor_headers
from test_course_source_routing_api import COURSE_ID, _client, _scanned_pdf, _upload

PROPOSAL = f"/admin/courses/{COURSE_ID}/source-routing/proposal"
ROUTING = f"/admin/courses/{COURSE_ID}/source-routing"


def test_a_complete_non_destructive_proposal_is_accepted_like_a_manual_confirm(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    _upload(client, "Lecture03.md", b"# Lecture 03\n\nBayes rule.")

    proposed = client.post(PROPOSAL, headers=professor_headers())

    assert proposed.status_code == 200, proposed.json()
    assert proposed.json()["confirmed"] is True
    assert client.get(ROUTING, headers=professor_headers()).json() == proposed.json()
    # The accepted assignment stays editable: the professor can reopen and confirm again.
    reopened = client.put(
        ROUTING,
        json={
            "source_revision": proposed.json()["source_revision"],
            "routes": [
                {**route, "role": "course_wide", "lecture_id": None}
                for route in proposed.json()["routes"]
            ],
        },
        headers=professor_headers(),
    )
    assert reopened.status_code == 200, reopened.json()
    assert reopened.json()["routes"][0]["role"] == "course_wide"


def test_a_proposal_that_would_delete_an_upload_waits_for_the_professor(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _upload(client, "Lecture03.md", b"# Lecture 03\n\nBayes rule.")
    _upload(client, "exam-protocols/README.md", b"# Historical protocols")

    proposed = client.post(PROPOSAL, headers=professor_headers()).json()

    assert proposed["confirmed"] is False
    uploads = client.app.state.canvas_workspace.layout.course_uploads_dir(COURSE_ID)
    assert (uploads / "exam-protocols" / "README.md").exists()


def test_a_source_needing_ocr_waits_for_the_professor(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _upload(client, "Lecture03.md", b"# Lecture 03\n\nBayes rule.")
    _upload(client, "scans/worksheet.pdf", _scanned_pdf())

    assert client.post(PROPOSAL, headers=professor_headers()).json()["confirmed"] is False


def test_a_regenerated_proposal_is_always_reviewed(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _upload(client, "Lecture03.md", b"# Lecture 03\n\nBayes rule.")
    assert client.post(PROPOSAL, headers=professor_headers()).json()["confirmed"] is True

    rebuilt = client.post(f"{PROPOSAL}?refresh=true", headers=professor_headers())

    assert rebuilt.status_code == 200
    assert rebuilt.json()["confirmed"] is False
