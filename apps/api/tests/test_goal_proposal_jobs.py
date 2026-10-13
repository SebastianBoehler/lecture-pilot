import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi import HTTPException

from lecturepilot.core.storage_layout import StorageLayout
from lecturepilot.learning_design import learning_goal_proposal_jobs as jobs


def test_background_proposals_record_progress_and_failures(tmp_path, monkeypatch) -> None:
    layout = StorageLayout(tmp_path)
    app = SimpleNamespace(state=SimpleNamespace(canvas_workspace=SimpleNamespace(layout=layout)))
    calls = []

    async def propose(app_, *, course_id, lecture_id, actor_user_id, refresh, **_kwargs):
        calls.append((course_id, lecture_id, actor_user_id, refresh))
        assert jobs.read_goal_proposal(layout, course_id, lecture_id).proposing()
        if lecture_id == "lecture-04":
            raise HTTPException(
                status_code=409, detail="Confirmed lecture sources are unavailable."
            )

    monkeypatch.setattr(jobs, "propose_lecture_goals", propose)
    jobs.mark_goal_proposals_running(layout, "course", ["lecture-03", "lecture-04"])

    async def run():
        task = jobs.start_goal_proposals(
            app,
            course_id="course",
            lecture_ids=["lecture-03", "lecture-04"],
            actor_user_id="prof",
            source_document=lambda *_: None,
        )
        await task

    asyncio.run(run())

    assert calls == [
        ("course", "lecture-03", "prof", False),
        ("course", "lecture-04", "prof", False),
    ]
    done = jobs.read_goal_proposal(layout, "course", "lecture-03")
    failed = jobs.read_goal_proposal(layout, "course", "lecture-04")
    assert (done.status, done.error_detail) == ("completed", None)
    assert (failed.status, failed.error_detail) == (
        "failed",
        "Confirmed lecture sources are unavailable.",
    )
    assert not failed.proposing()


def test_running_marker_expires_without_heartbeat(tmp_path) -> None:
    layout = StorageLayout(tmp_path)
    jobs.mark_goal_proposals_running(layout, "course", ["lecture-03"])
    job = jobs.read_goal_proposal(layout, "course", "lecture-03")

    assert job.proposing()
    assert not job.proposing(datetime.now(UTC) + jobs.GOAL_PROPOSAL_LEASE + timedelta(seconds=1))
