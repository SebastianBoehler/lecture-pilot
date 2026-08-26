import pytest
from pydantic import ValidationError

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_practice_contract import (
    section_target_assignments,
    validate_practice_candidate,
)
from lecturepilot.course_practice_design_models import PracticeDesign
from lecturepilot.course_practice_design_validation import (
    PracticeDesignValidationError,
    validate_learning_map_practice_contract,
)
from lecturepilot.learning_map import LearningMapGate, build_learning_map
from practice_design_test_helpers import proposal, target


def test_section_assignment_uses_the_section_containing_an_approved_anchor() -> None:
    design = _design()
    sections = [
        _source_section("overview", "This introduction does not carry the approved excerpt."),
        _source_section("evidence", "The cited evidence supports the conclusion."),
    ]

    assignments = section_target_assignments(design, sections)

    assert assignments["overview"] == ()
    assert assignments["evidence"] == design.targets


def test_section_assignment_fails_closed_when_no_section_contains_an_approved_anchor() -> None:
    design = _design()
    sections = [_source_section("overview", "Only unrelated introductory material.")]

    with pytest.raises(CanvasGenerationRepairableError, match="validated source anchor"):
        section_target_assignments(design, sections)


def test_canvas_rejects_checkpoint_in_an_unapproved_source_section() -> None:
    design = _design()
    document = _generated_document(design, source_ref="unrelated.md")

    with pytest.raises(CanvasGenerationRepairableError, match="approved source evidence"):
        validate_practice_candidate(document, design)


def test_learning_map_carries_the_complete_approved_teaching_contract() -> None:
    design = _design()

    gate = build_learning_map(_generated_document(design), design).gates[0]
    approved = design.targets[0]

    assert gate.target_invariant == approved.target_invariant
    assert gate.independent_exit_task == approved.independent_exit_task
    assert gate.independent_exit_surface_change == approved.independent_exit_surface_change
    assert gate.delayed_transfer_surface_change == approved.delayed_transfer_surface_change
    assert [item.model_dump() for item in gate.misconceptions] == [
        {
            "id": item.id,
            "description": item.description,
            "diagnostic_cue": item.diagnostic_cue,
        }
        for item in approved.misconceptions
    ]
    assert [item.model_dump() for item in gate.hint_ladder] == [
        {"level": item.level, "content": item.content} for item in approved.hint_ladder
    ]


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("target_invariant", "A different invariant."),
        ("independent_exit_surface_change", "Change the invariant."),
        ("delayed_transfer_surface_change", "Reuse the same task."),
        ("misconceptions", []),
        ("hint_ladder", []),
    ],
)
def test_learning_map_validator_rejects_mutated_teaching_contract(
    field: str, replacement: object
) -> None:
    design = _design()
    learning_map = build_learning_map(_generated_document(design), design)
    mutated = learning_map.model_copy(
        update={
            "gates": [learning_map.gates[0].model_copy(update={field: replacement})],
        }
    )

    with pytest.raises(PracticeDesignValidationError, match="differs"):
        validate_learning_map_practice_contract(mutated, design)


def test_practice_gate_rejects_an_implicitly_defaulted_teaching_contract() -> None:
    payload = {
        "id": "practice-derive-conclusion",
        "concept_id": "evidence",
        "title": "Derive a conclusion",
        "prompt": "Derive the conclusion from the stated evidence and justify the reasoning.",
        "evidence_criteria": [
            {
                "id": "cite-evidence",
                "description": "Cites the relevant evidence.",
                "required": True,
            }
        ],
        "transfer_prompt": "Derive a conclusion after the surface details change and justify it.",
        "independent_exit_task": "Derive a parallel conclusion independently.",
        "review_after_days": 7,
        "revision": "0" * 64,
        "section_id": "evidence",
        "source_ref": "lecture-01.md",
        "practice_target_id": "derive-conclusion",
    }

    with pytest.raises(ValidationError, match="target_invariant"):
        LearningMapGate.model_validate(payload, context={"build_revision": True})


def _design() -> PracticeDesign:
    draft = proposal()
    return PracticeDesign.create(
        course_id="course",
        lecture_id="lecture",
        lecture_title=draft.lecture_title,
        objective=draft.objective,
        planning_context=draft.planning_context,
        source_revision="a" * 64,
        targets=(target(),),
    )


def _source_section(section_id: str, text: str) -> CanvasSection:
    return CanvasSection(
        id=section_id,
        title=section_id.title(),
        source_ref="lecture-01.md",
        blocks=[CanvasBlock(id=f"{section_id}-text", type="paragraph", text=text)],
    )


def _generated_document(
    design: PracticeDesign, *, source_ref: str = "lecture-01.md"
) -> CanvasDocument:
    approved = design.targets[0]
    return CanvasDocument(
        id="course-lecture",
        course_id="course",
        lecture_id="lecture",
        title="Lecture",
        source_kind="generated",
        source_ref="lecture-01.md",
        workspace_path="course/index.md",
        sections=[
            CanvasSection(
                id="evidence",
                title="Evidence",
                source_ref=source_ref,
                blocks=[
                    CanvasBlock(
                        id=f"practice-{approved.id}",
                        type="checkpoint",
                        text=approved.baseline_task,
                    )
                ],
            )
        ],
    )
