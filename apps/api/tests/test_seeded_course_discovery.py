from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import student_headers
from canvas_workspace_fixtures import published_course_canvas
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace


def test_seeded_course_discovers_local_full_lecture_materials(tmp_path: Path) -> None:
    app = create_app()
    material_root = tmp_path / "materials"
    material_root.mkdir()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=material_root,
    )
    client = TestClient(app)
    for index, title in [
        (1, "Course Setup"),
        (2, "Generalization"),
        (3, "Bayes Classifier"),
        (4, "Kernel Methods"),
    ]:
        (material_root / f"Lecture{index:02d}-eng.tex").write_text(
            f"\\begin{{frame}}{{{title}}}{title}\\end{{frame}}",
            encoding="utf-8",
        )
        app.state.canvas_workspace.write_course_canvas(
            published_course_canvas("martius-ml", f"lecture-{index:02d}")
        )

    lectures = client.get("/courses/martius-ml/lectures", headers=student_headers("student01"))

    assert lectures.status_code == 200
    payload = lectures.json()
    assert [item["lecture"]["id"] for item in payload] == [
        "lecture-01",
        "lecture-02",
        "lecture-03",
        "lecture-04",
    ]
    assert payload[3]["lecture"]["title"] == "Kernel Methods"
    assert payload[3]["lecture"]["material_path"] == "Lecture04-eng.tex"
