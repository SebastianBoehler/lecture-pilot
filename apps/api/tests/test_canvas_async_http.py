import asyncio
from datetime import UTC, datetime, timedelta
import time

import pytest

from lecturepilot.course_canvas_generation_jobs import CanvasGenerationStore

from test_course_canvas_generation_service import _canvas
from test_course_canvas_targeted_repair import _course_client
from test_course_canvas_targeted_repair_resilience import headers, setup_failed_job


@pytest.mark.parametrize("repair", [False, True])
def test_async_http_returns_job_and_status_preserves_authority(tmp_path, monkeypatch, repair):
    if repair:
        client, path = setup_failed_job(tmp_path)
    else:
        client = _course_client(tmp_path)
        path = "/admin/courses/targeted-repair/lectures/lecture-01/canvas/draft"
    calls = []

    async def generate(*args, **kwargs):
        calls.append(kwargs["generation_id"])
        await asyncio.sleep(0.2)
        return _canvas()

    module = "course_canvas_repair_routes" if repair else "course_canvas_draft_routes"
    method = "repair_targeted_course_canvas_draft" if repair else "generate_course_canvas_draft"
    monkeypatch.setattr(f"lecturepilot.{module}.{method}", generate)
    request_headers = {**headers("async-http-request-0001"), "Prefer": "respond-async"}
    with client:
        response = client.post(path + ("/repair" if repair else ""), headers=request_headers)
        assert response.status_code == 202, response.text
        assert response.json()["status"] == "running"
        assert response.headers["Preference-Applied"] == "respond-async"
        original_read = CanvasGenerationStore.read

        def expired_read(self, **kwargs):
            job = original_read(self, **kwargs)
            return job.model_copy(update={"updated_at": datetime.now(UTC) - timedelta(minutes=2)})

        with monkeypatch.context() as expired:
            expired.setattr(CanvasGenerationStore, "read", expired_read)
            stalled = client.get(path + "/status", headers=request_headers)
            assert stalled.status_code == 503
            assert "resume saved work" in stalled.json()["detail"]
        foreign = client.get(path + "/status", headers=headers("unknown-request-0001"))
        assert foreign.status_code == 404
        for _ in range(100):
            status = client.get(path + "/status", headers=request_headers)
            assert status.status_code == 200
            if status.json()["status"] == "completed":
                break
            time.sleep(0.01)
        assert status.json()["status"] == "completed"
        assert "workspace_path" not in status.json()["canvas"]
        assert len(calls) == 1
