import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_practice_design_models import PracticeDesignProposal
from lecturepilot.course_practice_design_validation import (
    PracticeDesignValidationError,
    validate_practice_design,
)
from practice_design_test_helpers import proposal


def test_field_anchors_accept_whitespace_normalized_verbatim_routed_evidence() -> None:
    design = _anchored_proposal()

    validate_practice_design(
        design,
        source=_source(),
        allowed_source_paths=("lecture-01.md", "supplement.md"),
    )
    assert design.targets[0].outcome_anchor.excerpt == (
        "Bayes rule maps prior probabilities and likelihood evidence"
    )


def test_anchor_cannot_borrow_evidence_from_a_longer_routed_path() -> None:
    payload = proposal().model_dump(mode="json")
    target = payload["targets"][0]
    anchor = {
        "source_path": "lecture.md",
        "excerpt": "Evidence owned only by the longer routed path.",
    }
    for field in (
        "outcome_anchor",
        "target_invariant_anchor",
        "baseline_task_anchor",
        "independent_exit_task_anchor",
        "delayed_transfer_task_anchor",
    ):
        target[field] = anchor
    target["evidence_criteria"][0]["source_anchor"] = anchor
    target["misconceptions"][0]["source_anchor"] = anchor
    target["hint_ladder"][0]["source_anchor"] = anchor
    target["source_refs"] = ["lecture.md"]
    source = CanvasDocument(
        id="course-01-lecture-01",
        course_id="course-01",
        lecture_id="lecture-01",
        title="Routed path collision",
        source_kind="markdown",
        source_ref="lecture.md, lecture.md notes.txt",
        workspace_path="source.json",
        sections=[
            CanvasSection(
                id="longer-path",
                title="Longer path",
                source_ref="lecture.md notes.txt",
                blocks=[
                    CanvasBlock(
                        id="longer-path-evidence",
                        type="paragraph",
                        text="Evidence owned only by the longer routed path.",
                    )
                ],
            )
        ],
    )

    with pytest.raises(PracticeDesignValidationError, match="verbatim excerpt"):
        validate_practice_design(
            PracticeDesignProposal.model_validate(payload),
            source=source,
            allowed_source_paths=("lecture.md", "lecture.md notes.txt"),
        )


@pytest.mark.parametrize(
    "derived_suffix",
    (
        "pages 1–3",
        "slide 2",
        "sheet Results A1:B4",
        "frame 3",
        "frames 3, 4",
        "compiled preview",
    ),
)
def test_anchor_accepts_known_derived_refs_owned_by_its_routed_path(
    derived_suffix: str,
) -> None:
    source = _source()
    first = source.sections[0].model_copy(update={"source_ref": f"lecture-01.md {derived_suffix}"})

    validate_practice_design(
        _anchored_proposal(),
        source=source.model_copy(update={"sections": [first, *source.sections[1:]]}),
        allowed_source_paths=("lecture-01.md", "supplement.md"),
    )


@pytest.mark.parametrize(
    "anchor_location",
    (
        "outcome_anchor",
        "target_invariant_anchor",
        "baseline_task_anchor",
        "independent_exit_task_anchor",
        "delayed_transfer_task_anchor",
        "criterion",
        "misconception",
        "hint",
    ),
)
def test_every_required_field_anchor_must_quote_its_exact_routed_source(
    anchor_location: str,
) -> None:
    payload = _anchored_payload()
    target = payload["targets"][0]
    invalid_anchor = {
        "source_path": "lecture-01.md",
        "excerpt": "This statement appears only in the supplement.",
    }
    if anchor_location in {
        "outcome_anchor",
        "target_invariant_anchor",
        "baseline_task_anchor",
        "independent_exit_task_anchor",
        "delayed_transfer_task_anchor",
    }:
        target[anchor_location] = invalid_anchor
    elif anchor_location == "criterion":
        target["evidence_criteria"][0]["source_anchor"] = invalid_anchor
    elif anchor_location == "misconception":
        target["misconceptions"][0]["source_anchor"] = invalid_anchor
    else:
        target["hint_ladder"][0]["source_anchor"] = invalid_anchor

    with pytest.raises(PracticeDesignValidationError, match="verbatim excerpt"):
        validate_practice_design(
            PracticeDesignProposal.model_validate(payload),
            source=_source(),
            allowed_source_paths=("lecture-01.md", "supplement.md"),
        )


def _anchored_proposal() -> PracticeDesignProposal:
    return PracticeDesignProposal.model_validate(_anchored_payload())


def _anchored_payload() -> dict:
    payload = proposal().model_dump(mode="json")
    target = payload["targets"][0]
    anchor = {
        "source_path": "lecture-01.md",
        "excerpt": "Bayes rule maps prior probabilities\n  and likelihood evidence",
    }
    for field in (
        "outcome_anchor",
        "target_invariant_anchor",
        "baseline_task_anchor",
        "independent_exit_task_anchor",
        "delayed_transfer_task_anchor",
    ):
        target[field] = anchor
    target["evidence_criteria"][0]["source_anchor"] = anchor
    target["misconceptions"][0]["source_anchor"] = anchor
    target["hint_ladder"][0]["source_anchor"] = anchor
    return payload


def _source() -> CanvasDocument:
    return CanvasDocument(
        id="course-01-lecture-01",
        course_id="course-01",
        lecture_id="lecture-01",
        title="Bayes rule",
        source_kind="markdown",
        source_ref="lecture-01.md, supplement.md",
        workspace_path="source.json",
        sections=[
            CanvasSection(
                id="bayes-rule",
                title="Bayes rule",
                source_ref="lecture-01.md",
                blocks=[
                    CanvasBlock(
                        id="rule",
                        type="paragraph",
                        text=(
                            "Bayes rule maps prior probabilities\n"
                            "and likelihood evidence into posterior probabilities."
                        ),
                    )
                ],
            ),
            CanvasSection(
                id="supplement",
                title="Supplement",
                source_ref="supplement.md",
                blocks=[
                    CanvasBlock(
                        id="other",
                        type="paragraph",
                        text="This statement appears only in the supplement.",
                    )
                ],
            ),
        ],
    )
