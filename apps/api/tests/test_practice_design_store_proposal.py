from pathlib import Path

import pytest

from lecturepilot.course_practice_design_store import PracticeDesignStale, PracticeDesignStore
from lecturepilot.storage_layout import StorageLayout
from practice_design_test_helpers import passing_review, proposal, source_document


SOURCE_REVISION = "a" * 64
SOURCE_PATHS = {"lecture-01.md"}


def test_proposal_save_requires_the_expected_design_revision_or_absence(tmp_path: Path) -> None:
    store = PracticeDesignStore(StorageLayout(tmp_path))
    existing = store.save_proposal(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SOURCE_REVISION,
        proposal=proposal(),
        review=passing_review(),
        source=source_document(),
        allowed_source_paths=SOURCE_PATHS,
        expected_design_revision=None,
        expected_design_approval=None,
        expected_design_review=None,
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
            review=passing_review(),
            source=source_document(),
            allowed_source_paths=SOURCE_PATHS,
            expected_design_revision=None,
            expected_design_approval=None,
            expected_design_review=None,
        )

    replaced = store.save_proposal(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SOURCE_REVISION,
        proposal=changed_proposal,
        review=passing_review(),
        source=source_document(),
        allowed_source_paths=SOURCE_PATHS,
        expected_design_revision=existing.revision,
        expected_design_approval=None,
        expected_design_review=existing.quality_review,
    )

    assert replaced.objective == "Derive a changed conclusion from the cited evidence."
    with pytest.raises(PracticeDesignStale):
        PracticeDesignStore(StorageLayout(tmp_path / "empty")).save_proposal(
            course_id="course-01",
            lecture_id="lecture-01",
            source_revision=SOURCE_REVISION,
            proposal=changed_proposal,
            review=passing_review(),
            source=source_document(),
            allowed_source_paths=SOURCE_PATHS,
            expected_design_revision=existing.revision,
            expected_design_approval=None,
            expected_design_review=existing.quality_review,
        )


def test_proposal_save_rejects_an_approval_added_after_its_snapshot(tmp_path: Path) -> None:
    store = PracticeDesignStore(StorageLayout(tmp_path))
    existing = store.save_proposal(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SOURCE_REVISION,
        proposal=proposal(),
        review=passing_review(),
        source=source_document(),
        allowed_source_paths=SOURCE_PATHS,
        expected_design_revision=None,
        expected_design_approval=None,
        expected_design_review=None,
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
            review=passing_review(),
            source=source_document(),
            allowed_source_paths=SOURCE_PATHS,
            expected_design_revision=existing.revision,
            expected_design_approval=None,
            expected_design_review=existing.quality_review,
        )

    assert store.read(course_id="course-01", lecture_id="lecture-01") == approved
