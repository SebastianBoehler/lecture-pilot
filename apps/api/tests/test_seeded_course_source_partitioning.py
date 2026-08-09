from pathlib import Path

from auth_helpers import student_headers
from canvas_workspace_fixtures import publish_course_canvas, published_course_canvas
from test_course_source_partitioning import _client, _latex


def test_discovered_seeded_lecture_uses_the_same_authorization_catalog(tmp_path: Path) -> None:
    client = _client(tmp_path)
    material_root = client.app.state.canvas_workspace.material_root
    for number in range(1, 5):
        path = material_root / f"Lecture{number:02d}-eng.tex"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_latex(f"Lecture {number}", f"LECTURE-{number}"))
    publish_course_canvas(
        client.app.state.canvas_workspace,
        published_course_canvas("martius-ml", "lecture-04"),
    )

    response = client.get(
        "/courses/martius-ml/lectures/lecture-04/canvas/publication",
        headers=student_headers("student01"),
    )

    assert response.status_code == 200
    assert response.json()["published"] is True
