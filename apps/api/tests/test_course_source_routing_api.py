from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from auth_helpers import install_test_source_routing_planner, professor_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_builder_source import course_builder_source_document
from lecturepilot.lecture_source_manifest import read_lecture_source_manifest
from lecturepilot.source_bundle_canvas import SourceBundleCanvasError


COURSE_ID = "routing-course"


def test_professor_reviews_and_confirms_every_source_route(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _upload(client, "Lecture03.md", b"# Lecture 03\n\nBayes rule.")
    _upload(client, "exam-protocols/README.md", b"# Historical protocols")

    response = client.post(
        f"/admin/courses/{COURSE_ID}/source-routing/proposal",
        headers=professor_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["confirmed"] is False
    routes = {item["path"]: item for item in payload["routes"]}
    assert routes["Lecture03.md"]["role"] == "lecture"
    assert routes["Lecture03.md"]["lecture_id"] == "lecture-03"
    assert routes["exam-protocols/README.md"]["role"] == "excluded"
    assert routes["exam-protocols/README.md"]["lecture_id"] is None

    incomplete = client.put(
        f"/admin/courses/{COURSE_ID}/source-routing",
        json={"source_revision": payload["source_revision"], "routes": [routes["Lecture03.md"]]},
        headers=professor_headers(),
    )
    assert incomplete.status_code == 422
    assert "every uploaded source" in incomplete.json()["detail"]

    confirmed = client.put(
        f"/admin/courses/{COURSE_ID}/source-routing",
        json={"source_revision": payload["source_revision"], "routes": payload["routes"]},
        headers=professor_headers(),
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["confirmed"] is True


def test_generation_requires_current_routing_and_uses_only_generation_sources(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    _upload(
        client,
        "Lecture03.md",
        b"# Routed lecture\n\nBayes rule maps evidence into posterior probabilities.",
    )
    _upload(client, "exam-protocols/README.md", b"# Must not enter the canvas")

    with pytest.raises(SourceBundleCanvasError, match="Review and confirm source routing"):
        course_builder_source_document(client.app, COURSE_ID, "lecture-03")

    routing = client.post(
        f"/admin/courses/{COURSE_ID}/source-routing/proposal",
        headers=professor_headers(),
    ).json()
    confirmed = client.put(
        f"/admin/courses/{COURSE_ID}/source-routing",
        json={"source_revision": routing["source_revision"], "routes": routing["routes"]},
        headers=professor_headers(),
    )
    assert confirmed.status_code == 200

    document = course_builder_source_document(client.app, COURSE_ID, "lecture-03")

    assert document.title == "Language Models"
    manifest = read_lecture_source_manifest(
        client.app.state.canvas_workspace.layout.lecture_source_manifest_path(
            COURSE_ID, "lecture-03"
        ),
        COURSE_ID,
        "lecture-03",
    )
    assert [item.path for item in manifest.files] == ["Lecture03.md"]

    _upload(client, "Lecture04.md", b"# Newly uploaded source")
    with pytest.raises(SourceBundleCanvasError, match="Review and confirm source routing"):
        course_builder_source_document(client.app, COURSE_ID, "lecture-03")

    stale = client.put(
        f"/admin/courses/{COURSE_ID}/source-routing",
        json={"source_revision": routing["source_revision"], "routes": routing["routes"]},
        headers=professor_headers(),
    )
    assert stale.status_code == 409
    assert "changed" in stale.json()["detail"]


def test_professor_can_rebuild_a_confirmed_source_proposal(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _upload(client, "Lecture03.md", b"# Lecture 03\n\nBayes rule.")
    proposal = client.post(
        f"/admin/courses/{COURSE_ID}/source-routing/proposal",
        headers=professor_headers(),
    ).json()
    confirmed = client.put(
        f"/admin/courses/{COURSE_ID}/source-routing",
        json={"source_revision": proposal["source_revision"], "routes": proposal["routes"]},
        headers=professor_headers(),
    )
    assert confirmed.json()["confirmed"] is True

    cached = client.post(
        f"/admin/courses/{COURSE_ID}/source-routing/proposal",
        headers=professor_headers(),
    )
    rebuilt = client.post(
        f"/admin/courses/{COURSE_ID}/source-routing/proposal?refresh=true",
        headers=professor_headers(),
    )

    assert cached.json()["confirmed"] is True
    assert rebuilt.status_code == 200
    assert rebuilt.json()["confirmed"] is False


def test_replacing_the_lecture_schedule_invalidates_confirmed_routing(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _upload(client, "Lecture03.md", b"# Lecture 03\n\nBayes rule maps evidence into decisions.")
    routing = client.post(
        f"/admin/courses/{COURSE_ID}/source-routing/proposal", headers=professor_headers()
    ).json()
    confirmed = client.put(
        f"/admin/courses/{COURSE_ID}/source-routing",
        json={"source_revision": routing["source_revision"], "routes": routing["routes"]},
        headers=professor_headers(),
    )
    assert confirmed.status_code == 200

    replaced = client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Routing Course",
            "target": "full-course",
            "replace_lectures": True,
            "lectures": [
                {
                    "number": "04",
                    "title": "Machine Translation",
                    "date": "2026-07-08",
                    "material_path": "Lecture03.md",
                }
            ],
        },
        headers=professor_headers(),
    )
    assert replaced.status_code == 200

    unavailable = client.get(
        f"/admin/courses/{COURSE_ID}/source-routing", headers=professor_headers()
    )
    assert unavailable.status_code == 409
    refreshed = client.post(
        f"/admin/courses/{COURSE_ID}/source-routing/proposal", headers=professor_headers()
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["confirmed"] is False
    with pytest.raises(SourceBundleCanvasError, match="Review and confirm source routing"):
        course_builder_source_document(client.app, COURSE_ID, "lecture-04")


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "course",
    )
    client = TestClient(app)
    install_test_source_routing_planner(client)
    created = client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Routing Course",
            "target": "full-course",
            "replace_lectures": True,
            "lectures": [
                {
                    "number": "03",
                    "title": "Language Models",
                    "date": "2026-07-01",
                    "material_path": "Lecture03.md",
                }
            ],
        },
        headers=professor_headers(),
    )
    assert created.status_code == 200
    assert created.json()["course"]["id"] == COURSE_ID
    return client


def _upload(client: TestClient, path: str, content: bytes) -> None:
    response = client.post(
        f"/admin/courses/{COURSE_ID}/materials",
        data={"path": path},
        files={"file": (Path(path).name, content)},
        headers=professor_headers(),
    )
    assert response.status_code == 200
