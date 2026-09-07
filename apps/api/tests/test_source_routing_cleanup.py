from pathlib import Path

from auth_helpers import professor_headers
from test_course_source_routing_api import COURSE_ID, _client, _upload


def test_confirmation_removes_unused_uploads_and_refreshes_routing(tmp_path: Path):
    client = _client(tmp_path)
    _upload(client, "Lecture03.md", b"# Bayes\n\nSee [figure](images/keep.png).")
    _upload(client, "images/keep.png", _png())
    _upload(client, "unused.md", b"Unused source")
    proposal = client.post(
        f"/admin/courses/{COURSE_ID}/source-routing/proposal", headers=professor_headers()
    ).json()
    for route in proposal["routes"]:
        if route["path"] != "Lecture03.md":
            route.update(role="excluded", lecture_id=None)
    layout = client.app.state.canvas_workspace.layout
    unused = next(r for r in proposal["routes"] if r["path"] == "unused.md")
    normalized = layout.course_normalized_dir(COURSE_ID) / unused["sha256"]
    normalized.mkdir(parents=True)
    (normalized / "text.md").write_text("Unused normalized text")
    response = client.put(
        f"/admin/courses/{COURSE_ID}/source-routing",
        json=proposal,
        headers=professor_headers(),
    )
    assert response.status_code == 200, response.text
    uploads = layout.course_uploads_dir(COURSE_ID)
    assert not (uploads / "unused.md").exists()
    assert not (normalized / "text.md").exists()
    assert (uploads / "images/keep.png").exists()
    assert (uploads / "Lecture03.md").exists()
    assert response.json()["source_revision"] != proposal["source_revision"]
    refreshed = client.get(
        f"/admin/courses/{COURSE_ID}/source-routing", headers=professor_headers()
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["confirmed"]
    assert {r["path"] for r in refreshed.json()["routes"]} == {"Lecture03.md", "images/keep.png"}


def test_confirmation_keeps_existing_canvas_references(tmp_path: Path):
    client = _client(tmp_path)
    _upload(client, "Lecture03.md", b"# Bayes")
    _upload(client, "old.md", b"Previously published evidence")
    proposal = client.post(
        f"/admin/courses/{COURSE_ID}/source-routing/proposal", headers=professor_headers()
    ).json()
    for route in proposal["routes"]:
        if route["path"] == "old.md":
            route.update(role="excluded", lecture_id=None)
    root = client.app.state.canvas_workspace.layout.course_root(COURSE_ID)
    canvas = root / "canvas" / "lectures" / "lecture-03" / "index.md"
    canvas.parent.mkdir(parents=True)
    canvas.write_text('source_ref: "uploads/old.md"')
    response = client.put(
        f"/admin/courses/{COURSE_ID}/source-routing",
        json=proposal,
        headers=professor_headers(),
    )
    assert response.status_code == 200, response.text
    assert (root / "source/uploads/old.md").exists()


def _png():
    from io import BytesIO
    from PIL import Image

    stream = BytesIO()
    Image.new("RGB", (2, 2)).save(stream, format="PNG")
    return stream.getvalue()


def test_cleanup_failure_restores_uploads_index_and_routing(tmp_path, monkeypatch):
    import pytest
    import lecturepilot.course_source_cleanup as cleanup

    client = _client(tmp_path)
    _upload(client, "Lecture03.md", b"# Bayes")
    _upload(client, "unused.md", b"Unused source")
    proposal = client.post(
        f"/admin/courses/{COURSE_ID}/source-routing/proposal", headers=professor_headers()
    ).json()
    for route in proposal["routes"]:
        if route["path"] == "unused.md":
            route.update(role="excluded", lecture_id=None)
    layout = client.app.state.canvas_workspace.layout
    routing_path = layout.course_source_routing_path(COURSE_ID)
    original = routing_path.read_bytes()

    def fail(**kwargs):
        assert not (layout.course_uploads_dir(COURSE_ID) / "unused.md").exists()
        raise OSError("simulated index write failure")

    monkeypatch.setattr(cleanup, "refresh_course_source_index", fail)
    with pytest.raises(OSError, match="simulated index"):
        client.put(
            f"/admin/courses/{COURSE_ID}/source-routing", json=proposal, headers=professor_headers()
        )
    assert (layout.course_uploads_dir(COURSE_ID) / "unused.md").read_bytes() == b"Unused source"
    assert routing_path.read_bytes() == original
    assert "unused.md" in layout.course_source_index_path(COURSE_ID).read_text()


def test_cleanup_preserves_transitive_tex_dependencies(tmp_path):
    from lecturepilot.source_index import refresh_course_source_index
    from lecturepilot.source_retention import retained_source_paths
    from lecturepilot.course_source_routing_models import CourseSourceRoute
    from lecturepilot.storage_layout import StorageLayout

    layout = StorageLayout(tmp_path)
    uploads = layout.course_uploads_dir(COURSE_ID)
    (uploads / "chapters").mkdir(parents=True)
    (uploads / "main.tex").write_text(r"\input{chapters/lesson}")
    (uploads / "chapters/lesson.tex").write_text(r"\includegraphics{figure}")
    (uploads / "chapters/figure.png").write_bytes(_png())
    (uploads / "unused.md").write_text("Unused")
    index = refresh_course_source_index(
        course_id=COURSE_ID,
        uploads_dir=uploads,
        index_path=layout.course_source_index_path(COURSE_ID),
    )
    routes = [
        CourseSourceRoute(
            path=f.path,
            sha256=f.sha256,
            kind=f.kind,
            role="course_wide" if f.path == "main.tex" else "excluded",
        )
        for f in index.files
    ]
    assert retained_source_paths(layout, COURSE_ID, index, routes, []) == {
        "main.tex",
        "chapters/lesson.tex",
        "chapters/figure.png",
    }


def test_storage_only_cleanup_preserves_teaching_revision_but_new_upload_invalidates(tmp_path):
    import json
    from lecturepilot.course_canvas_repairs import lecture_source_revision

    client = _client(tmp_path)
    _upload(client, "Lecture03.md", b"# Bayes")
    _upload(client, "unused.md", b"Unused source")
    proposal = client.post(
        f"/admin/courses/{COURSE_ID}/source-routing/proposal", headers=professor_headers()
    ).json()
    for route in proposal["routes"]:
        if route["path"] == "unused.md":
            route.update(role="excluded", lecture_id=None)
    proposal["confirmed"] = True
    layout = client.app.state.canvas_workspace.layout
    layout.course_source_routing_path(COURSE_ID).write_text(json.dumps(proposal))
    source = next(r for r in proposal["routes"] if r["path"] == "Lecture03.md")
    path = layout.lecture_source_manifest_path(COURSE_ID, "lecture-03")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "course_id": COURSE_ID,
                "lecture_id": "lecture-03",
                "files": [{"path": source["path"], "sha256": source["sha256"]}],
            }
        )
    )
    before = lecture_source_revision(layout, course_id=COURSE_ID, lecture_id="lecture-03")
    response = client.put(
        f"/admin/courses/{COURSE_ID}/source-routing", json=proposal, headers=professor_headers()
    )
    assert response.status_code == 200, response.text
    assert not (layout.course_uploads_dir(COURSE_ID) / "unused.md").exists()
    assert lecture_source_revision(layout, course_id=COURSE_ID, lecture_id="lecture-03") == before
    _upload(client, "new.md", b"New source")
    assert lecture_source_revision(layout, course_id=COURSE_ID, lecture_id="lecture-03") != before
