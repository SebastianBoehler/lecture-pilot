from pathlib import Path

import pytest

from lecturepilot.course_practice_design_store import PracticeDesignStale, PracticeDesignStore
from lecturepilot.storage_layout import StorageLayout
from practice_design_test_helpers import proposal


SOURCE_REVISION = "a" * 64
SOURCE_PATHS = {"lecture-01.md"}


def test_proposal_save_requires_the_expected_design_revision_or_absence(tmp_path: Path) -> None:
    store = PracticeDesignStore(StorageLayout(tmp_path))
    existing = store.save_proposal(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SOURCE_REVISION,
        proposal=proposal(),
        allowed_source_paths=SOURCE_PATHS,
        expected_design_revision=None,
        expected_design_approval=None,
    )
    changed_proposal = proposal().model_copy(
        update={"objective": "Derive a changed conclusion from the cited evidence."}
    )

    with pytest.raises(PracticeDesignStale):
        store.save_proposal(
            course_id="course-01",
            lecture_id="lecture-01",
            source_revision=SOURCE_REVISION,
            proposal=changed_proposal,
            allowed_source_paths=SOURCE_PATHS,
            expected_design_revision=None,
            expected_design_approval=None,
        )

    replaced = store.save_proposal(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SOURCE_REVISION,
        proposal=changed_proposal,
        allowed_source_paths=SOURCE_PATHS,
        expected_design_revision=existing.revision,
        expected_design_approval=None,
    )

    assert replaced.objective == "Derive a changed conclusion from the cited evidence."
    with pytest.raises(PracticeDesignStale):
        PracticeDesignStore(StorageLayout(tmp_path / "empty")).save_proposal(
            course_id="course-01",
            lecture_id="lecture-01",
            source_revision=SOURCE_REVISION,
            proposal=changed_proposal,
            allowed_source_paths=SOURCE_PATHS,
            expected_design_revision=existing.revision,
            expected_design_approval=None,
        )


def test_proposal_save_rejects_an_approval_added_after_its_snapshot(tmp_path: Path) -> None:
    store = PracticeDesignStore(StorageLayout(tmp_path))
    existing = store.save_proposal(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SOURCE_REVISION,
        proposal=proposal(),
        allowed_source_paths=SOURCE_PATHS,
        expected_design_revision=None,
        expected_design_approval=None,
    )
    approved = store.approve(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SOURCE_REVISION,
        design_revision=existing.revision,
        approved_by="professor-01",
    )

    with pytest.raises(PracticeDesignStale):
        store.save_proposal(
            course_id="course-01",
            lecture_id="lecture-01",
            source_revision=SOURCE_REVISION,
            proposal=proposal(),
            allowed_source_paths=SOURCE_PATHS,
            expected_design_revision=existing.revision,
            expected_design_approval=None,
        )

    assert store.read(course_id="course-01", lecture_id="lecture-01") == approved
