import json
from datetime import UTC, datetime, timedelta

from api_test_client import workspace_client
from auth_helpers import professor_headers
from lecturepilot.course_canvas_generation_jobs import CanvasGenerationStore
from lecturepilot.course_canvas_generation_service import CANVAS_GENERATION_LEASE_SECONDS


def test_running_job_without_a_worker_is_reported_as_resumable(tmp_path):
    api = workspace_client(tmp_path)
    layout = api.app.state.canvas_workspace.layout
    store = CanvasGenerationStore(layout, lease_seconds=CANVAS_GENERATION_LEASE_SECONDS)
    job, owns = store.begin(
        course_id="course-a",
        lecture_id="lecture-01",
        actor_user_id="prof01",
        request_key="interrupted-run-0001",
    )
    assert owns and job.status == "running"
    path = next((layout.course_root("course-a") / "builder" / "generations").rglob("*.json"))
    record = json.loads(path.read_text())
    record["updated_at"] = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
    path.write_text(json.dumps(record))

    response = api.get(
        "/admin/courses/course-a/lectures/lecture-01/canvas/draft", headers=professor_headers()
    )
    assert response.status_code == 404
    assert response.headers["X-Generation-Status"] == "failed"
    assert response.headers["X-Generation-Error-Code"] == "interrupted"
    assert response.headers["X-Generation-Repairable"] == "true"
    assert "interrupted" in response.json()["detail"]
