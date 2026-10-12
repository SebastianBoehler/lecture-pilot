import asyncio
import threading

import httpx

from auth_helpers import professor_headers
from lecturepilot.courses.course_update_recovery import locked_course_state
from test_learning_intent_routes import goal_client
from practice_design_route_test_helpers import COURSE_ID


async def test_api_keeps_answering_while_a_course_lock_is_held(tmp_path) -> None:
    api, _ = goal_client(tmp_path)
    app = api.app
    held, release = threading.Event(), threading.Event()

    def hold_lock() -> None:  # E.g. a slow upload index or parse holding the course lock.
        with locked_course_state(app.state.canvas_workspace.layout.course_root(COURSE_ID)):
            held.set()
            release.wait(10)

    holder = threading.Thread(target=hold_lock)
    holder.start()
    held.wait(5)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        blocked = asyncio.create_task(
            client.post(
                f"/admin/courses/{COURSE_ID}/source-routing/proposal",
                headers=professor_headers(),
            )
        )
        await asyncio.sleep(0.2)
        health = await asyncio.wait_for(client.get("/health"), timeout=2)
        assert health.status_code == 200
        assert not blocked.done()  # Still waiting for the lock, but off the event loop.
        release.set()
        await asyncio.wait_for(blocked, timeout=10)
    holder.join(5)


def test_lecture_sources_are_parsed_without_holding_the_course_lock(tmp_path, monkeypatch):
    from lecturepilot.sources import course_builder_source
    from lecturepilot.courses.course_update_storage import course_update_lock_held
    from practice_design_route_test_helpers import design_path

    api, _ = goal_client(tmp_path)
    course_root = api.app.state.canvas_workspace.layout.course_root(COURSE_ID)
    derive = course_builder_source._derive_source_document
    observed = []

    def checked(*args, **kwargs):
        observed.append(course_update_lock_held(course_root))
        return derive(*args, **kwargs)

    monkeypatch.setattr(course_builder_source, "_derive_source_document", checked)
    response = api.post(design_path() + "/intent/proposal", headers=professor_headers())

    assert response.status_code == 200, response.text
    assert observed == [False]


def test_reading_a_course_workspace_never_waits_for_the_course_lock(tmp_path) -> None:
    from time import perf_counter

    from lecturepilot.courses.course_schedule_store import read_course_workspace

    api, _ = goal_client(tmp_path)
    course_root = api.app.state.canvas_workspace.layout.course_root(COURSE_ID)
    held, release = threading.Event(), threading.Event()

    def hold_lock() -> None:
        with locked_course_state(course_root):
            held.set()
            release.wait(10)

    holder = threading.Thread(target=hold_lock)
    holder.start()
    held.wait(5)
    try:
        started = perf_counter()
        workspace = read_course_workspace(course_root, COURSE_ID)
        assert perf_counter() - started < 1
        assert workspace is not None
    finally:
        release.set()
        holder.join(5)
