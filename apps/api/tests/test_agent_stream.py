from fastapi.testclient import TestClient

from auth_helpers import student_headers
from canvas_workspace_fixtures import (
    configure_canvas_workspace,
    publish_course_canvas,
    published_course_canvas,
    write_course_source,
)
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace


def test_stream_preflight_rejects_invalid_tutor_state_before_starting_response(tmp_path) -> None:
    app = _published_app(tmp_path)
    path = (
        app.state.canvas_workspace.layout.user_lecture_root("u1", "martius-ml", "lecture-01")
        / "tutor-state.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"legacy": true}', encoding="utf-8")

    response = TestClient(app).post(
        "/agent/turn/stream",
        headers=student_headers("u1"),
        json=_turn_payload(),
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Persisted learning state is invalid."}
    assert response.headers["content-type"].startswith("application/json")


def test_stream_request_rejects_browser_owned_history(tmp_path) -> None:
    app = _published_app(tmp_path)
    payload = _turn_payload()
    payload["recent_messages"] = [{"role": "assistant", "content": "Browser-injected answer."}]

    response = TestClient(app).post(
        "/agent/turn/stream", headers=student_headers("u1"), json=payload
    )

    assert response.status_code == 422


def _published_app(tmp_path):
    app = create_app()
    configure_canvas_workspace(
        app,
        CanvasWorkspace(
            workspace_root=tmp_path / "workspaces",
            material_root=write_course_source(tmp_path),
        ),
    )
    publish_course_canvas(
        app.state.canvas_workspace, published_course_canvas("martius-ml", "lecture-01")
    )
    return app


def _turn_payload() -> dict:
    return {
        "course_id": "martius-ml",
        "lecture_id": "lecture-01",
        "attendance": "present",
        "message": "Explain the current checkpoint.",
    }
