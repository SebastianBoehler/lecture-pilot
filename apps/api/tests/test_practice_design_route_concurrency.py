import asyncio
from threading import Event, Thread

from auth_helpers import professor_headers

from lecturepilot.course_practice_design_store import PracticeDesignStore
from lecturepilot.course_update_storage import course_update_lock_held
from lecturepilot import course_practice_design_routes
from test_practice_design_routes import COURSE_ID, _Planner, _client, _design_path, _proposal_path


def test_refresh_conflicts_instead_of_overwriting_a_concurrent_professor_edit(tmp_path) -> None:
    client = _client(tmp_path)
    client.app.state.practice_design_planner = _Planner()
    original = client.post(_proposal_path(), headers=professor_headers()).json()
    paused = _PausingPlanner()
    client.app.state.practice_design_planner = paused
    outcome: dict[str, object] = {}

    request = Thread(
        target=lambda: outcome.setdefault(
            "response",
            client.post(f"{_proposal_path()}?refresh=true", headers=professor_headers()),
        )
    )
    request.start()
    assert paused.started.wait(timeout=5)
    edited = client.put(
        _design_path(),
        headers=professor_headers(),
        json={
            "source_revision": original["source_revision"],
            "practice_design_revision": original["revision"],
            "lecture_title": original["lecture_title"],
            "objective": "Calculate a revised posterior from stated evidence.",
            "targets": original["targets"],
        },
    )
    assert edited.status_code == 200
    paused.resume.set()
    request.join(timeout=5)

    assert not request.is_alive()
    response = outcome["response"]
    assert response.status_code == 409
    assert (
        client.get(_design_path(), headers=professor_headers()).json()["revision"]
        == edited.json()["revision"]
    )


def test_update_and_approval_hold_shared_lock_across_source_and_design_mutation(
    tmp_path, monkeypatch
) -> None:
    client = _client(tmp_path)
    client.app.state.practice_design_planner = _Planner()
    design = client.post(_proposal_path(), headers=professor_headers()).json()
    course_root = client.app.state.canvas_workspace.layout.course_root(COURSE_ID)
    observed: list[bool] = []
    original_context = course_practice_design_routes._source_context
    original_update = PracticeDesignStore.update
    original_approve = PracticeDesignStore.approve

    def locked_context(*args, **kwargs):
        observed.append(course_update_lock_held(course_root))
        return original_context(*args, **kwargs)

    def locked_update(self, **kwargs):
        observed.append(course_update_lock_held(course_root))
        return original_update(self, **kwargs)

    def locked_approve(self, **kwargs):
        observed.append(course_update_lock_held(course_root))
        return original_approve(self, **kwargs)

    monkeypatch.setattr(course_practice_design_routes, "_source_context", locked_context)
    monkeypatch.setattr(PracticeDesignStore, "update", locked_update)
    monkeypatch.setattr(PracticeDesignStore, "approve", locked_approve)
    updated = client.put(
        _design_path(),
        headers=professor_headers(),
        json={
            "source_revision": design["source_revision"],
            "practice_design_revision": design["revision"],
            "lecture_title": design["lecture_title"],
            "objective": "Calculate a revised posterior from stated evidence.",
            "targets": design["targets"],
        },
    )
    approved = client.post(
        f"{_design_path()}/approve",
        headers=professor_headers(),
        json={
            "source_revision": updated.json()["source_revision"],
            "practice_design_revision": updated.json()["revision"],
        },
    )

    assert updated.status_code == 200
    assert approved.status_code == 200
    assert observed == [True, True, True, True]


class _PausingPlanner(_Planner):
    def __init__(self) -> None:
        self.started = Event()
        self.resume = Event()

    async def propose(self, **kwargs):
        self.started.set()
        await asyncio.to_thread(self.resume.wait)
        return await super().propose(**kwargs)
