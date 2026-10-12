import asyncio
from datetime import timedelta
from types import SimpleNamespace

import pytest

from lecturepilot.authoring import course_canvas_generation_service as service
from lecturepilot.canvas.canvas_models import CanvasDocument
from lecturepilot.authoring.course_canvas_generation_jobs import CanvasGenerationStore
from lecturepilot.llm.generation_slots import (
    BACKGROUND_GENERATION_SLOTS,
    background_generation_slot,
)
from lecturepilot.core.storage_layout import StorageLayout
from test_course_canvas_generation_service import _canvas


def _store(tmp_path) -> CanvasGenerationStore:
    return CanvasGenerationStore(StorageLayout(tmp_path), lease_seconds=45)


def _start(app, store, lecture_id: str, generate):
    return service.run_idempotent_canvas_generation(
        app=app,
        store=store,
        course_id="course-1",
        lecture_id=lecture_id,
        actor_user_id="professor-1",
        request_key=f"request-key-{lecture_id}",
        generate=generate,
        wait_for_completion=False,
    )


@pytest.mark.asyncio
async def test_background_jobs_queue_for_two_shared_slots(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(service, "CANVAS_GENERATION_HEARTBEAT_SECONDS", 0.01)
    touched: list[str] = []
    store = _store(tmp_path)
    original_touch = store.touch

    def touch(job, **kwargs):
        touched.append(job.lecture_id)
        return original_touch(job, **kwargs)

    store.touch = touch
    app = SimpleNamespace(state=SimpleNamespace())
    release = asyncio.Event()
    running: list[str] = []
    peak = 0

    async def generate_for(lecture_id: str):
        nonlocal peak
        running.append(lecture_id)
        peak = max(peak, len(running))
        await release.wait()
        running.remove(lecture_id)
        return _canvas()

    def generator(lecture_id: str):
        async def generate(_generation_id: str, _attempt: int) -> CanvasDocument:
            return await generate_for(lecture_id)

        return generate

    lectures = ["lecture-01", "lecture-02", "lecture-03"]
    jobs = [await _start(app, store, lecture, generator(lecture)) for lecture in lectures]
    await asyncio.sleep(0.1)

    assert BACKGROUND_GENERATION_SLOTS == 2
    assert running == lectures[:2]
    assert "lecture-03" in touched  # The queued job's lease stays alive.
    assert all(job.status == "running" for job in jobs)

    release.set()
    tasks = list(app.state.canvas_generation_tasks.values())
    await asyncio.wait_for(asyncio.gather(*tasks), timeout=2)
    assert peak == 2


@pytest.mark.asyncio
async def test_practice_exams_wait_for_slots_held_by_other_jobs(monkeypatch) -> None:
    from lecturepilot.exams import practice_exam_generation_service as exams

    app = SimpleNamespace(
        state=SimpleNamespace(
            practice_exam_store=SimpleNamespace(write=lambda **kwargs: None),
            practice_exam_generation_store=SimpleNamespace(
                lease=timedelta(seconds=30),
                renew=lambda *args, **kwargs: None,
                complete=lambda *args, **kwargs: None,
                read=lambda **kwargs: None,
            ),
        )
    )
    exam_started = asyncio.Event()

    async def generate_practice_exam(*args, **kwargs):
        exam_started.set()
        return SimpleNamespace(id="exam-1", questions=[])

    monkeypatch.setattr(exams, "generate_practice_exam", generate_practice_exam)
    monkeypatch.setattr(exams, "public_practice_exam", lambda exam: exam.id)
    entered, release = asyncio.Event(), asyncio.Event()

    async def canvas_job():
        async with background_generation_slot(app):
            entered.set()
            await release.wait()

    holders = [asyncio.create_task(canvas_job()) for _ in range(BACKGROUND_GENERATION_SLOTS)]
    await entered.wait()
    exam = asyncio.create_task(
        exams._generate_owned(
            app,
            job=SimpleNamespace(course_id="course-1", attempt=1),
            request_key="practice-exam-key-0001",
            context=SimpleNamespace(user_id="student-1"),
            input_data=SimpleNamespace(ppi_source_ids=[]),
        )
    )
    await asyncio.sleep(0.05)
    assert not exam_started.is_set()
    release.set()
    assert await asyncio.wait_for(exam, timeout=1) == "exam-1"
    await asyncio.gather(*holders)
