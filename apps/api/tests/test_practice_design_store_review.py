from pathlib import Path

import pytest

from lecturepilot.course_practice_design_models import PracticeDesignProposal, PracticeDesignUpdate
from lecturepilot.course_practice_design_review_models import (
    REVIEW_DIMENSIONS,
    PracticeDesignReviewResult,
)
from lecturepilot.course_practice_design_store import PracticeDesignStale, PracticeDesignStore
from lecturepilot.course_practice_design_validation import PracticeDesignValidationError
from lecturepilot.storage_layout import StorageLayout
from practice_design_review_test_helpers import passing_review, source_document
from practice_design_test_helpers import proposal, target
from test_practice_design_store import PATHS, SRC, _save, _update


def test_revision_is_canonical_and_excludes_semantic_review_text(tmp_path: Path) -> None:
    store = PracticeDesignStore(StorageLayout(tmp_path))
    saved = _save(store)
    warning = PracticeDesignReviewResult(
        checks=[
            {
                "dimension": dimension,
                "severity": "warning" if index == 0 else "pass",
                "summary": "A visible noncritical concern." if index == 0 else "Passed.",
                "target_ids": ["derive-conclusion"] if index == 0 else [],
                "supporting_anchors": (
                    [{"source_path": "lecture-01.md", "excerpt": "evidence"}] if index == 0 else []
                ),
            }
            for index, dimension in enumerate(REVIEW_DIMENSIONS)
        ]
    )

    reviewed = store.save_review(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SRC,
        design_revision=saved.revision,
        review=warning,
        source=source_document(),
        allowed_source_paths=PATHS,
        expected_design_review=saved.quality_review,
        expected_design_approval=None,
    )

    assert reviewed.revision == saved.revision
    assert reviewed.quality_review != saved.quality_review


def test_save_and_update_reject_unknown_routed_source_paths(tmp_path: Path) -> None:
    store = PracticeDesignStore(StorageLayout(tmp_path))
    ungrounded = PracticeDesignProposal(
        **{**proposal().model_dump(), "targets": [target(source_refs=["other-lecture.md"])]}
    )

    with pytest.raises(PracticeDesignValidationError, match="unrouted"):
        store.save_proposal(
            course_id="course-01",
            lecture_id="lecture-01",
            source_revision=SRC,
            proposal=ungrounded,
            review=passing_review(),
            source=source_document(),
            allowed_source_paths=PATHS,
            expected_design_revision=None,
            expected_design_approval=None,
            expected_design_review=None,
        )
    saved = _save(store)
    update = PracticeDesignUpdate(
        **{**_update(saved).model_dump(), "targets": [target(source_refs=["other.md"])]}
    )

    with pytest.raises(PracticeDesignValidationError, match="unrouted"):
        store.update(
            course_id="course-01",
            lecture_id="lecture-01",
            current_source_revision=SRC,
            update=update,
            source=source_document(),
            allowed_source_paths=PATHS,
        )


def test_rereview_detects_concurrent_approval_and_clears_snapshotted_approval(
    tmp_path: Path,
) -> None:
    store = PracticeDesignStore(StorageLayout(tmp_path))
    saved = _save(store)
    approved = store.approve(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SRC,
        design_revision=saved.revision,
        approved_by="professor-01",
    )
    arguments = {
        "course_id": "course-01",
        "lecture_id": "lecture-01",
        "source_revision": SRC,
        "design_revision": approved.revision,
        "review": passing_review(),
        "source": source_document(),
        "allowed_source_paths": PATHS,
        "expected_design_review": approved.quality_review,
    }

    with pytest.raises(PracticeDesignStale):
        store.save_review(**arguments, expected_design_approval=None)

    reviewed = store.save_review(
        **arguments,
        expected_design_approval=approved.approval,
    )
    assert reviewed.approval is None
