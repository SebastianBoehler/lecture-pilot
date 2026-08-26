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
