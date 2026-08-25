from pathlib import Path

import pytest
from pydantic import ValidationError

from lecturepilot.course_practice_design_models import (
    PracticeDesign,
    PracticeDesignApprovalInput,
    PracticeDesignUpdate,
    PracticeDesignProposal,
    PracticeHint,
    PracticeTarget,
)
from lecturepilot.course_practice_design_store import (
    PracticeDesignApprovalRequired,
    PracticeDesignStale,
    PracticeDesignStore,
    PracticeDesignUnavailable,
)
from lecturepilot.course_practice_design_validation import (
    PracticeDesignValidationError,
    validate_canvas_practice_contract,
)
from lecturepilot.storage_layout import StorageLayout
from practice_design_test_helpers import document as _document
from practice_design_test_helpers import proposal as _proposal
from practice_design_test_helpers import target as _target


SRC = "a" * 64
PATHS = {"lecture-01.md"}


def test_save_proposal_round_trips_a_canonical_revision(tmp_path: Path) -> None:
    store = PracticeDesignStore(StorageLayout(tmp_path))
    proposal = _proposal()

    saved = store.save_proposal(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SRC,
        proposal=proposal,
        allowed_source_paths=PATHS,
    )

    assert len(saved.revision) == 64
    assert store.read(course_id="course-01", lecture_id="lecture-01") == saved


def test_revision_is_canonical_and_excludes_approval(tmp_path: Path) -> None:
    store = PracticeDesignStore(StorageLayout(tmp_path))
    proposal = _proposal()
    saved = store.save_proposal(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SRC,
        proposal=proposal,
        allowed_source_paths=PATHS,
    )

    approved = store.approve(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SRC,
        design_revision=saved.revision,
        approved_by="professor-01",
    )
    rebuilt = PracticeDesign.create(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SRC,
        **proposal.model_dump(mode="python"),
    )

    assert approved.revision == saved.revision == rebuilt.revision
    assert approved.approval is not None


@pytest.mark.parametrize("count", [0, 9])
def test_proposal_rejects_target_counts_outside_one_through_eight(count: int) -> None:
    targets = [_proposal().targets[0] for _ in range(count)]

    with pytest.raises(ValidationError):
        PracticeDesignProposal(
            lecture_title="Practice design",
            objective="Derive the conclusion independently from the cited evidence.",
            targets=targets,
        )


def test_models_reject_invalid_ids_duplicate_task_variants_and_unordered_hints() -> None:
    target = _proposal().targets[0]

    with pytest.raises(ValidationError):
        target.model_copy(update={"id": "invalid_id"}).__class__(
            **{**target.model_dump(), "id": "invalid_id"}
        )
    with pytest.raises(ValidationError):
        PracticeTarget(
            **{
                **target.model_dump(),
                "independent_exit_task": target.baseline_task,
            }
        )
    with pytest.raises(ValidationError):
        PracticeTarget(
            **{
                **target.model_dump(),
                "hint_ladder": [
                    PracticeHint(level="cue", content="Notice the evidence relation."),
                    PracticeHint(level="prompt", content="Identify the key evidence."),
                ],
            }
        )
    with pytest.raises(ValidationError):
        PracticeTarget(
            **{
                **target.model_dump(),
                "hint_ladder": [
                    PracticeHint(level="prompt", content="Identify the key evidence."),
                    PracticeHint(level="prompt", content="Name the relevant source."),
                ],
            }
        )
    with pytest.raises(ValidationError, match="unique"):
        PracticeDesignProposal(
            lecture_title="Practice design",
            objective="Derive the conclusion independently from the cited evidence.",
            targets=[target, target],
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"title": " "},
        {"outcome": " "},
        {"baseline_task": " "},
        {"independent_exit_task": " "},
        {"delayed_transfer_task": " "},
        {"evidence_criteria": [{"id": "cite-evidence", "description": " "}]},
        {"misconceptions": [{"id": "ignore-evidence", "description": " ", "diagnostic_cue": " "}]},
        {"hint_ladder": [{"level": "prompt", "content": " "}]},
    ],
)
def test_models_reject_whitespace_only_required_content(changes: dict[str, object]) -> None:
    target = _proposal().targets[0]

    with pytest.raises(ValidationError):
        PracticeTarget(**{**target.model_dump(), **changes})


def test_contract_collections_are_immutable() -> None:
    proposal = _proposal()
    target = proposal.targets[0]

    assert all(
        isinstance(value, tuple)
        for value in (
            proposal.targets,
            target.source_refs,
            target.evidence_criteria,
            target.misconceptions,
            target.hint_ladder,
        )
    )
    with pytest.raises(AttributeError):
        target.source_refs.append("other-lecture.md")


def test_save_and_update_reject_unknown_routed_source_paths(tmp_path: Path) -> None:
    store = PracticeDesignStore(StorageLayout(tmp_path))
    proposal = PracticeDesignProposal(
        **{**_proposal().model_dump(), "targets": [_target(source_refs=["other-lecture.md"])]}
    )

    with pytest.raises(PracticeDesignValidationError, match="unrouted"):
        store.save_proposal(
            course_id="course-01",
            lecture_id="lecture-01",
            source_revision=SRC,
            proposal=proposal,
            allowed_source_paths=PATHS,
        )
    saved = _save(store)
    update = PracticeDesignUpdate(
        **{**_update(saved).model_dump(), "targets": [_target(source_refs=["other.md"])]}
    )

    with pytest.raises(PracticeDesignValidationError, match="unrouted"):
        store.update(
            course_id="course-01",
            lecture_id="lecture-01",
            current_source_revision=SRC,
            update=update,
            allowed_source_paths=PATHS,
        )


def test_update_clears_approval_and_requires_current_versions(tmp_path: Path) -> None:
    store = PracticeDesignStore(StorageLayout(tmp_path))
    saved = _save(store)
    approved = store.approve(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SRC,
        design_revision=saved.revision,
        approved_by="professor-01",
    )
    changed = store.update(
        course_id="course-01",
        lecture_id="lecture-01",
        current_source_revision=SRC,
        update=_update(approved, objective="Derive a changed, independent conclusion."),
        allowed_source_paths=PATHS,
    )
    assert changed.approval is None
    assert changed.revision != approved.revision
    with pytest.raises(PracticeDesignApprovalRequired):
        store.require_approved(course_id="course-01", lecture_id="lecture-01", source_revision=SRC)
    with pytest.raises(PracticeDesignStale):
        store.update(
            course_id="course-01",
            lecture_id="lecture-01",
            current_source_revision=SRC,
            update=_update(approved),
            allowed_source_paths=PATHS,
        )


def test_store_rejects_stale_and_corrupt_persisted_designs(tmp_path: Path) -> None:
    layout = StorageLayout(tmp_path)
    store = PracticeDesignStore(layout)
    saved = _save(store)

    with pytest.raises(PracticeDesignStale):
        store.require_approved(
            course_id="course-01",
            lecture_id="lecture-01",
            source_revision="b" * 64,
            design_revision=saved.revision,
        )
    path = layout.lecture_practice_design_path("course-01", "lecture-01")
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(PracticeDesignUnavailable, match="invalid"):
        store.read(course_id="course-01", lecture_id="lecture-01")


def test_approval_input_and_canvas_contract_are_exact() -> None:
    design = PracticeDesign.create(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SRC,
        **_proposal().model_dump(mode="python"),
    )
    approval = PracticeDesignApprovalInput(
        source_revision=SRC, practice_design_revision=design.revision
    )
    document = _document(design.targets[0].baseline_task)

    assert approval.practice_design_revision == design.revision
    validate_canvas_practice_contract(document, design)
    with pytest.raises(PracticeDesignValidationError, match="baseline task"):
        validate_canvas_practice_contract(
            _document("Altered task"),
            design,
        )


def _save(store: PracticeDesignStore) -> PracticeDesign:
    return store.save_proposal(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SRC,
        proposal=_proposal(),
        allowed_source_paths=PATHS,
    )


def _update(design: PracticeDesign, *, objective: str | None = None) -> PracticeDesignUpdate:
    return PracticeDesignUpdate(
        source_revision=design.source_revision,
        practice_design_revision=design.revision,
        lecture_title=design.lecture_title,
        objective=objective or design.objective,
        targets=design.targets,
    )
