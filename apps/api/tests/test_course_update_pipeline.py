from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import confirm_source_routing, professor_headers
from lecturepilot.app import create_app
from lecturepilot.canvas.canvas_workspace import CanvasWorkspace
from lecturepilot.sources.course_source_routing import read_source_routing
from lecturepilot.sources.lecture_source_revision import lecture_source_revision

COURSE = "update-demo"


def test_apply_extends_confirmed_routing_and_proposes_goals_for_new_lectures(
    tmp_path: Path, monkeypatch
) -> None:
    started = _record_proposals(monkeypatch)
    client = _routed_course(tmp_path)
    layout = client.app.state.canvas_workspace.layout
    before = {lid: _revision(client, lid) for lid in ("lecture-01", "lecture-02")}
    update_id = _create_update(client)
    _upload(client, f"updates/{update_id}/materials", "Lecture02.tex", _deck("Two", "Changed"))
    _upload(
        client,
        f"updates/{update_id}/materials",
        "Lecture03.tex",
        _deck("Lecture 03: Regularization", "Overfitting"),
    )
    analysis = _get(client, f"updates/{update_id}")
    new = next(item for item in analysis["candidates"] if item["action"] == "new")
    assert new["title"] == "Regularization"

    applied = _apply(client, update_id, analysis["candidates"])

    assert applied["routing"] == "confirmed"
    assert applied["new_lecture_ids"] == ["lecture-03"]
    assert started == [(COURSE, ["lecture-03"])]
    routing = read_source_routing(layout.course_source_routing_path(COURSE), COURSE)
    routes = {route.path: (route.role, route.lecture_id) for route in routing.routes}
    assert routing.confirmed
    assert routes["Lecture03.tex"] == ("lecture", "lecture-03")
    assert routes["macros.sty"] == ("course_wide", None)
    assert _revision(client, "lecture-01") == before["lecture-01"]
    assert _revision(client, "lecture-02") != before["lecture-02"]
    manifest = layout.lecture_source_manifest_path(COURSE, "lecture-03").read_text()
    assert "Lecture03.tex" in manifest and "macros.sty" in manifest
    # The routing is current, so the new lecture's sources are usable right away.
    readiness = _get(client, "lectures/lecture-03/practice-design/readiness")
    assert readiness["ready_for_generation"] is False


def test_files_assigned_to_every_existing_lecture_become_course_wide(
    tmp_path: Path, monkeypatch
) -> None:
    _record_proposals(monkeypatch)
    client = _routed_course(tmp_path)
    before = _revision(client, "lecture-01")
    update_id = _create_update(client)
    _upload(client, f"updates/{update_id}/materials", "notation.md", b"# Notation")
    selections = [
        {**lecture, "file_paths": ["notation.md"]}
        for lecture in _get(client, f"updates/{update_id}")["existing_lectures"]
    ]

    applied = _apply(client, update_id, selections)

    layout = client.app.state.canvas_workspace.layout
    routing = read_source_routing(layout.course_source_routing_path(COURSE), COURSE)
    route = next(item for item in routing.routes if item.path == "notation.md")
    assert applied["routing"] == "confirmed" and applied["new_lecture_ids"] == []
    assert (route.role, route.lecture_id) == ("course_wide", None)
    assert _revision(client, "lecture-01") != before  # A shared file changes every lecture.


def test_unconfirmed_routing_still_requires_confirmation_after_apply(
    tmp_path: Path, monkeypatch
) -> None:
    started = _record_proposals(monkeypatch)
    client = _routed_course(tmp_path)
    _upload(client, "materials", "extra.md", b"# Extra")  # Routing no longer current.
    update_id = _create_update(client)
    _upload(client, f"updates/{update_id}/materials", "Lecture03.tex", _deck("Three", "New"))

    applied = _apply(client, update_id, _get(client, f"updates/{update_id}")["candidates"])

    assert applied["routing"] == "needs_review"
    assert started == []


def _record_proposals(monkeypatch) -> list:
    started = []
    monkeypatch.setattr(
        "lecturepilot.courses.course_update_routes.start_goal_proposals",
        lambda app, *, course_id, lecture_ids, **_kwargs: started.append((course_id, lecture_ids)),
    )
    return started


def _routed_course(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    client = TestClient(app)
    created = client.post(
        "/admin/course-workspaces",
        headers=professor_headers(),
        json={
            "course_title": "Update Demo",
            "target": "full-course",
            "lectures": [
                {"number": "01", "title": "One", "date": "2026-05-06"},
                {"number": "02", "title": "Two", "date": "2026-05-13"},
            ],
        },
    )
    assert created.status_code == 200, created.text
    _upload(client, "materials", "Lecture01.tex", _deck("One", "Basics"))
    _upload(client, "materials", "Lecture02.tex", _deck("Two", "Gradients"))
    _upload(client, "materials", "macros.sty", b"\\newcommand{\\R}{\\mathbb{R}}")
    confirm_source_routing(client, COURSE, {"macros.sty": ("course_wide", None)})
    return client


def _revision(client: TestClient, lecture_id: str) -> str | None:
    layout = client.app.state.canvas_workspace.layout
    return lecture_source_revision(layout, course_id=COURSE, lecture_id=lecture_id)


def _create_update(client: TestClient) -> str:
    response = client.post(f"/admin/courses/{COURSE}/updates", headers=professor_headers())
    assert response.status_code == 200
    return response.json()["update_id"]


def _apply(client: TestClient, update_id: str, lectures: list[dict]) -> dict:
    fields = ("lecture_id", "number", "title", "date", "file_paths")
    response = client.post(
        f"/admin/courses/{COURSE}/updates/{update_id}/apply",
        headers=professor_headers(),
        json={"lectures": [{key: item.get(key) for key in fields} for item in lectures]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _upload(client: TestClient, route: str, path: str, content: bytes) -> None:
    response = client.post(
        f"/admin/courses/{COURSE}/{route}",
        headers=professor_headers(),
        data={"path": path},
        files={"file": (Path(path).name, content, "text/plain")},
    )
    assert response.status_code == 200, response.text


def _get(client: TestClient, route: str) -> dict:
    response = client.get(f"/admin/courses/{COURSE}/{route}", headers=professor_headers())
    assert response.status_code == 200, response.text
    return response.json()


def _deck(title: str, section: str) -> bytes:
    return (
        f"\\documentclass{{beamer}}\n\\title{{{title}}}\n\\begin{{document}}\n"
        f"\\section{{{section}}}\n\\begin{{frame}}{{{section}}}Text\\end{{frame}}\n"
        "\\end{document}\n"
    ).encode()
