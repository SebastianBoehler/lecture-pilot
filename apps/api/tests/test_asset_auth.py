from pathlib import Path

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from auth_helpers import student_headers


def test_course_asset_requires_authentication(tmp_path: Path) -> None:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    asset_path = (
        app.state.canvas_workspace.layout.course_uploads_dir("martius-ml") / "figures" / "risk.png"
    )
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"\x89PNG\r\n")
    client = TestClient(app)
    url = "/course-assets/martius-ml/lecture-03/figures/risk.png"

    assert client.get(url).status_code == 401
    response = client.get(url, headers=student_headers("student01"))

    assert response.status_code == 200
    assert response.content.startswith(b"\x89PNG")
