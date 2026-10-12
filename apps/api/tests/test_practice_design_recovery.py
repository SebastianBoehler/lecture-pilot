from pathlib import Path

import pytest

from auth_helpers import professor_headers
from lecturepilot.learning_design.course_learning_intent import goal_for
from lecturepilot.learning_design.course_learning_intent_proposal import LearningIntentProposal
from lecturepilot.learning_design.course_learning_intent_store import LearningIntentStore
from lecturepilot.learning_design.course_practice_design_store import PracticeDesignStale
from lecturepilot.core.storage_layout import StorageLayout
from practice_design_route_test_helpers import COURSE_ID, design_path
from practice_design_test_helpers import proposal, source_document
from test_learning_intent_routes import goal_client

SOURCE_REVISION = "a" * 64
LECTURE_ID = "lecture-01"
INVALID = b'{"legacy": true}'


def test_goal_save_replaces_only_the_invalid_file_in_its_snapshot(tmp_path: Path) -> None:
    store, path = _invalid_store(tmp_path)
    snapshot = store.snapshot(course_id="course-01", lecture_id=LECTURE_ID)

    saved = _save(store, expected_invalid_digest=snapshot.invalid_digest)

    assert snapshot.design is None and snapshot.invalid_digest is not None
    assert store.read(course_id="course-01", lecture_id=LECTURE_ID) == saved


@pytest.mark.parametrize("replacement", ["changed", "missing"])
def test_goal_save_rejects_an_invalid_file_changed_after_its_snapshot(
    tmp_path: Path, replacement: str
) -> None:
    store, path = _invalid_store(tmp_path)
    snapshot = store.snapshot(course_id="course-01", lecture_id=LECTURE_ID)
    if replacement == "missing":
        path.unlink()
    else:
        path.write_bytes(b'{"legacy": "changed"}')

    with pytest.raises(PracticeDesignStale, match="changed"):
        _save(store, expected_invalid_digest=snapshot.invalid_digest)
    if replacement == "changed":
        with pytest.raises(PracticeDesignStale, match="changed"):
            _save(store)  # An unreadable design is never overwritten without observing it.


def test_goal_proposal_recovers_an_unreadable_stored_design(tmp_path: Path) -> None:
    api, calls = goal_client(tmp_path)
    path = _route_design_file(api)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(INVALID)

    response = api.post(design_path() + "/intent/proposal", headers=professor_headers())

    assert response.status_code == 200, response.text
    assert len(calls) == 2
    assert api.get(design_path(), headers=professor_headers()).json() == response.json()


def _invalid_store(tmp_path: Path):
    store = LearningIntentStore(StorageLayout(tmp_path))
    path = store.layout.lecture_practice_design_path("course-01", LECTURE_ID)
    path.parent.mkdir(parents=True)
    path.write_bytes(INVALID)
    return store, path


def _save(store, *, expected_invalid_digest=None):
    draft = proposal()
    return store.save_goals(
        expected=None,
        expected_invalid_digest=expected_invalid_digest,
        course_id="course-01",
        lecture_id=LECTURE_ID,
        source_revision=SOURCE_REVISION,
        proposal=LearningIntentProposal(
            lecture_title=draft.lecture_title,
            objective=draft.objective,
            planning_context=draft.planning_context,
            goals=tuple(goal_for(target) for target in draft.targets),
        ),
        source=source_document(),
        allowed_source_paths={"lecture-01.md"},
    )


def _route_design_file(api) -> Path:
    return api.app.state.canvas_workspace.layout.lecture_practice_design_path(COURSE_ID, LECTURE_ID)
