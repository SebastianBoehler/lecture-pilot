import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from threading import Barrier
from time import sleep

import httpx

from lecturepilot import agent_turn_orchestration, workspace_capability
from lecturepilot.source_capability_guard import shared_source_access
from source_capability_test_helpers import published_source_workspace
from test_practice_exam_api import _client
from test_source_capability_binding import _executor
from test_strict_model_payload import _turn
from auth_helpers import student_headers


async def test_exam_http_connection_can_finish_while_one_renewed_job_continues(tmp_path):
    client, planner = _client(tmp_path)
    release = asyncio.Event()
    original = planner.plan
    calls = []

    async def slow_plan(**kwargs):
        calls.append(kwargs)
        await release.wait()
        return await original(**kwargs)

    planner.plan = slow_plan
    client.app.state.practice_exam_generation_store.lease = timedelta(seconds=0.09)
    headers = {**student_headers("student-a"), "Idempotency-Key": "background-exam-key"}
    url = "/courses/martius-ml/practice-exam-generations"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=client.app), base_url="http://testserver"
    ) as browser:
        result = await browser.post(url, headers=headers, json={"question_count": 20})
        assert result.status_code == 202
        assert result.json()["status"] == "running"
        replay = await browser.post(url, headers=headers, json={"question_count": 20})
        assert replay.status_code == 409
        assert len(calls) == 1
        release.set()
        task = next(iter(client.app.state.practice_exam_generation_tasks.values()))
        await task
        status = await browser.get(url + "/status", headers=headers)
        assert status.json()["status"] == "completed"
        assert status.json()["attempt"] == 1
        assert (
            len(
                client.app.state.practice_exam_store.list(
                    user_id="student-a", course_id="martius-ml"
                )
            )
            == 1
        )


def test_source_identity_is_validated_once_and_shared_reads_can_overlap(tmp_path, monkeypatch):
    workspace = published_source_workspace(tmp_path)
    validations = []
    original = workspace_capability._validated_source_binding

    def validate(*args):
        validations.append(1)
        return original(*args)

    monkeypatch.setattr(workspace_capability, "_validated_source_binding", validate)
    executor = _executor(workspace)
    for tool, args in [
        ("read", {"path": "/course/source/uploads/current.md"}),
        ("grep", {"path": "/course/source/uploads", "pattern": "secret"}),
        ("find", {"path": "/course/source/uploads"}),
    ]:
        assert executor.execute(tool, args)["ok"]
    assert len(validations) == 1
    barrier = Barrier(2)

    def reader():
        with shared_source_access(
            workspace.layout.course_root("course-a"),
            workspace.layout.course_canvas_dir("course-a", "lecture-open"),
        ):
            barrier.wait(timeout=2)

    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(reader) for _ in range(2)]
        for job in jobs:
            job.result(timeout=3)


def test_slow_source_io_does_not_consume_regex_budget(tmp_path):
    executor = _executor(published_source_workspace(tmp_path))
    root = executor.workspace_fs.capability.roots[-1]
    from contextlib import contextmanager

    @contextmanager
    def slow_guard():
        sleep(0.15)
        with root.read_guard():
            yield

    executor.workspace_fs.capability = replace(
        executor.workspace_fs.capability,
        roots=(*executor.workspace_fs.capability.roots[:-1], replace(root, read_guard=slow_guard)),
    )
    result = executor.execute("grep", {"path": "/course/source/uploads", "pattern": "secret"})
    assert result["ok"] and result["matches"]


async def test_tutor_stream_sends_heartbeat_while_waiting_for_model(monkeypatch):
    async def wait(*args, **kwargs):
        await asyncio.Event().wait()

    monkeypatch.setattr(agent_turn_orchestration, "complete_agent_turn", wait)
    monkeypatch.setattr(agent_turn_orchestration, "STREAM_HEARTBEAT_SECONDS", 0.01)
    stream = agent_turn_orchestration.agent_turn_events(None, turn=_turn())
    assert await anext(stream) == "\n"
    await stream.aclose()
