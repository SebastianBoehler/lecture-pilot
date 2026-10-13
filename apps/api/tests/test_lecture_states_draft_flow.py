import asyncio
import time

from auth_helpers import professor_headers
from test_course_canvas_targeted_repair import _course_client
from test_course_canvas_targeted_repair_resilience import headers

COURSE = "targeted-repair"
DRAFT = f"/admin/courses/{COURSE}/lectures/lecture-01/canvas/draft"


def test_an_accepted_async_draft_reports_generating_then_its_failure(tmp_path, monkeypatch):
    client = _course_client(tmp_path)
    release = asyncio.Event()

    async def generate(*_args, **_kwargs):
        await release.wait()
        raise RuntimeError("Section 2 could not be grounded in the sources.")

    monkeypatch.setattr(
        "lecturepilot.authoring.course_canvas_draft_routes.generate_course_canvas_draft", generate
    )
    with client:
        assert _lecture(client)[2:] == ("none", None, "generate_draft")
        request = {**headers("lecture-state-draft-0001"), "Prefer": "respond-async"}
        accepted = client.post(DRAFT, headers=request)
        assert accepted.status_code == 202, accepted.text

        assert _lecture(client)[2:] == ("generating", None, "wait")

        client.portal.call(release.set)
        for _ in range(200):
            state = _lecture(client)
            if state[2] != "generating":
                break
            time.sleep(0.01)

    assert state[1:] == (
        "approved",
        "failed",
        "Section 2 could not be grounded in the sources.",
        "retry_draft",
    )


def _lecture(client) -> tuple:
    response = client.get(f"/admin/courses/{COURSE}/lecture-states", headers=professor_headers())
    assert response.status_code == 200, response.text
    item = response.json()["lectures"][0]
    return item["sources"], item["goals"], item["draft"], item["draft_error"], item["next_action"]
