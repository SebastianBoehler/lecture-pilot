from pathlib import Path

import pytest
from pydantic import ValidationError

from lecturepilot.course_practice_design_models import (
    PracticeDesign,
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
from approved_practice_design_helpers import approved_practice_design, store_design


SRC = "a" * 64


def test_stored_design_round_trips_and_revision_excludes_goal_approval(tmp_path: Path) -> None:
    layout = StorageLayout(tmp_path)
    store = PracticeDesignStore(layout)
    approved = store_design(layout, _design())
    pending = _design(reviewed=False)
    unapproved = pending.model_copy(
        update={"learning_intent": pending.learning_intent.model_copy(update={"approval": None})}
    )

    assert store.read(course_id="course-01", lecture_id="lecture-01") == approved
    assert approved.revision == PracticeDesign.create(**_payload(unapproved)).revision
    assert approved.learning_intent.approval is not None


@pytest.mark.parametrize("count", [0, 9])
def test_proposal_rejects_target_counts_outside_one_through_eight(count: int) -> None:
    proposal = _proposal()
    targets = [proposal.targets[0] for _ in range(count)]

    with pytest.raises(ValidationError):
        PracticeDesignProposal(
            lecture_title="Practice design",
            objective="Derive the conclusion independently from the cited evidence.",
            planning_context=proposal.planning_context,
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
                    PracticeHint(
                        level="cue",
                        content="Notice the evidence relation.",
                        source_anchor=target.outcome_anchor,
                    ),
                    PracticeHint(
                        level="prompt",
                        content="Identify the key evidence.",
                        source_anchor=target.outcome_anchor,
                    ),
                ],
            }
        )
    with pytest.raises(ValidationError):
        PracticeTarget(
            **{
                **target.model_dump(),
                "hint_ladder": [
                    PracticeHint(
                        level="prompt",
                        content="Identify the key evidence.",
                        source_anchor=target.outcome_anchor,
                    ),
                    PracticeHint(
                        level="prompt",
                        content="Name the relevant source.",
                        source_anchor=target.outcome_anchor,
                    ),
                ],
            }
        )
    with pytest.raises(ValidationError, match="unique"):
        PracticeDesignProposal(
            lecture_title="Practice design",
            objective="Derive the conclusion independently from the cited evidence.",
            planning_context=_proposal().planning_context,
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


def test_generation_requires_current_goal_approval_and_reviewed_teaching(tmp_path: Path) -> None:
    layout = StorageLayout(tmp_path)
    store = PracticeDesignStore(layout)
    design = _design(reviewed=False)
    store_design(
        layout,
        PracticeDesign.create(
            **{
                **_payload(design),
                "learning_intent": design.learning_intent.model_copy(update={"approval": None}),
            }
        ),
    )
    with pytest.raises(PracticeDesignApprovalRequired, match="learning goals"):
        store.require_approved(course_id="course-01", lecture_id="lecture-01", source_revision=SRC)
    store_design(layout, design)
    with pytest.raises(PracticeDesignApprovalRequired, match="automatic repair"):
        store.require_approved(course_id="course-01", lecture_id="lecture-01", source_revision=SRC)
    assert (
        store.require_approved(
            course_id="course-01",
            lecture_id="lecture-01",
            source_revision=SRC,
            allow_pending_implementation=True,
        )
        == design
    )


def test_store_rejects_stale_and_corrupt_persisted_designs(tmp_path: Path) -> None:
    layout = StorageLayout(tmp_path)
    store = PracticeDesignStore(layout)
    saved = store_design(layout, _design())

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


def test_canvas_contract_is_exact() -> None:
    design = _design()
    validate_canvas_practice_contract(_document(design.targets[0].baseline_task), design)
    with pytest.raises(PracticeDesignValidationError, match="baseline task"):
        validate_canvas_practice_contract(_document("Altered task"), design)


def _design(*, reviewed: bool = True) -> PracticeDesign:
    return approved_practice_design(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SRC,
        targets=_proposal().targets,
        reviewed=reviewed,
    )


def _payload(design: PracticeDesign) -> dict:
    return design.model_dump(mode="python", exclude={"revision", "quality_review"})
