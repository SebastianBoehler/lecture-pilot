import asyncio
from pathlib import Path
from threading import Event, Thread

import pytest

from auth_helpers import professor_headers
from lecturepilot.course_practice_design_store import PracticeDesignStale, PracticeDesignStore
from lecturepilot.storage_layout import StorageLayout
from practice_design_route_test_helpers import (
    COURSE_ID,
    Planner,
    client as make_client,
    design_path,
    proposal_path,
)
from practice_design_test_helpers import passing_review, proposal, source_document


SOURCE_REVISION = "a" * 64
LECTURE_ID = "lecture-01"


def test_store_replaces_only_the_invalid_file_in_its_snapshot(tmp_path: Path) -> None:
    store = PracticeDesignStore(StorageLayout(tmp_path))
    path = store.layout.lecture_practice_design_path("course-01", LECTURE_ID)
    path.parent.mkdir(parents=True)
    path.write_bytes(b'{"legacy": true}')

    snapshot = store.snapshot(course_id="course-01", lecture_id=LECTURE_ID)
    saved = _save(store, expected_invalid_digest=snapshot.invalid_digest)

    assert snapshot.design is None
    assert snapshot.invalid_digest is not None
    assert store.read(course_id="course-01", lecture_id=LECTURE_ID) == saved


def test_store_rejects_a_changed_invalid_file_after_its_snapshot(tmp_path: Path) -> None:
    store = PracticeDesignStore(StorageLayout(tmp_path))
    path = store.layout.lecture_practice_design_path("course-01", LECTURE_ID)
    path.parent.mkdir(parents=True)
    path.write_bytes(b'{"legacy": true}')
    snapshot = store.snapshot(course_id="course-01", lecture_id=LECTURE_ID)
    changed = b'{"legacy": "changed"}'
    path.write_bytes(changed)

    with pytest.raises(PracticeDesignStale, match="changed"):
        _save(store, expected_invalid_digest=snapshot.invalid_digest)

    assert path.read_bytes() == changed


@pytest.mark.parametrize("replacement", ["missing", "valid"])
def test_store_rejects_an_invalid_file_replaced_after_its_snapshot(
    tmp_path: Path, replacement: str
) -> None:
    store = PracticeDesignStore(StorageLayout(tmp_path / "observed"))
    path = store.layout.lecture_practice_design_path("course-01", LECTURE_ID)
    path.parent.mkdir(parents=True)
    path.write_bytes(b'{"legacy": true}')
    snapshot = store.snapshot(course_id="course-01", lecture_id=LECTURE_ID)
    replacement_payload = None
    if replacement == "missing":
        path.unlink()
    else:
        valid_store = PracticeDesignStore(StorageLayout(tmp_path / "valid"))
        _save(valid_store)
        valid_path = valid_store.layout.lecture_practice_design_path("course-01", LECTURE_ID)
        replacement_payload = valid_path.read_bytes()
        path.write_bytes(replacement_payload)

    with pytest.raises(PracticeDesignStale, match="changed"):
        _save(store, expected_invalid_digest=snapshot.invalid_digest)

    if replacement == "missing":
        assert not path.exists()
    else:
        assert path.read_bytes() == replacement_payload


def test_snapshot_preserves_missing_and_valid_states(tmp_path: Path) -> None:
    store = PracticeDesignStore(StorageLayout(tmp_path))

    missing = store.snapshot(course_id="course-01", lecture_id=LECTURE_ID)
    saved = _save(store)
    valid = store.snapshot(course_id="course-01", lecture_id=LECTURE_ID)

    assert missing.design is None
    assert missing.invalid_digest is None
    assert valid.design == saved
    assert valid.invalid_digest is None


def test_route_recovers_the_exact_invalid_design_observed_before_generation(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    planner = Planner()
    client.app.state.practice_design_planner = planner
    path = _route_design_file(client)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'{"legacy": true}')

    response = client.post(proposal_path(), headers=professor_headers())

    assert response.status_code == 200, response.json()
    assert planner.calls == 1
    assert client.get(design_path(), headers=professor_headers()).json() == response.json()


def test_route_conflicts_when_invalid_design_changes_during_generation(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    planner = _PausingPlanner()
    client.app.state.practice_design_planner = planner
    path = _route_design_file(client)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'{"legacy": true}')
    outcome: dict[str, object] = {}
    request = Thread(
        target=lambda: outcome.setdefault(
            "response", client.post(proposal_path(), headers=professor_headers())
        )
    )

    request.start()
    assert planner.started.wait(timeout=5)
    changed = b'{"legacy": "changed"}'
    path.write_bytes(changed)
    planner.resume.set()
    request.join(timeout=5)

    assert not request.is_alive()
    assert outcome["response"].status_code == 409
    assert path.read_bytes() == changed


def test_route_maps_an_invalid_snapshot_read_without_calling_the_model(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    planner = Planner()
    client.app.state.practice_design_planner = planner
    path = _route_design_file(client)
    path.mkdir(parents=True)

    response = client.post(proposal_path(), headers=professor_headers())

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Stored practice design could not be read. Generate a new learning plan."
    )
    assert planner.calls == 0


def test_route_maps_an_invalid_design_created_during_generation(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    planner = _PausingPlanner()
    client.app.state.practice_design_planner = planner
    path = _route_design_file(client)
    outcome: dict[str, object] = {}
    request = Thread(
        target=lambda: outcome.setdefault(
            "response", client.post(proposal_path(), headers=professor_headers())
        )
    )

    request.start()
    assert planner.started.wait(timeout=5)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'{"legacy": true}')
    planner.resume.set()
    request.join(timeout=5)

    assert not request.is_alive()
    assert outcome["response"].status_code == 500
    assert path.read_bytes() == b'{"legacy": true}'


class _PausingPlanner(Planner):
    def __init__(self) -> None:
        self.started = Event()
        self.resume = Event()

    async def propose(self, **kwargs):
        self.started.set()
        await asyncio.to_thread(self.resume.wait)
        return await super().propose(**kwargs)


def _save(store: PracticeDesignStore, *, expected_invalid_digest: str | None = None):
    return store.save_proposal(
        course_id="course-01",
        lecture_id=LECTURE_ID,
        source_revision=SOURCE_REVISION,
        proposal=proposal(),
        review=passing_review(),
        source=source_document(),
        allowed_source_paths={"lecture-01.md"},
        expected_design_revision=None,
        expected_design_approval=None,
        expected_design_review=None,
        expected_invalid_digest=expected_invalid_digest,
    )


def _route_design_file(client) -> Path:
    return client.app.state.canvas_workspace.layout.lecture_practice_design_path(
        COURSE_ID, LECTURE_ID
    )
