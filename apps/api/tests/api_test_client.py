"""Shared API client for route tests that need an isolated course workspace."""

from pathlib import Path

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace


def workspace_client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    return TestClient(app)
