import pytest
from pydantic import ValidationError
from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_markdown import read_document_source, write_document_source
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_practice_contract import (
    practice_prompt_instruction,
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


def test_section_prompt_lists_only_applicable_canonical_checkpoint_ids() -> None:
    design = _design()

    instruction = practice_prompt_instruction(design, targets=())

    assert f"practice-{design.targets[0].id}" not in instruction
    assert design.targets[0].baseline_task not in instruction


def test_canvas_writer_receives_approved_context_without_hidden_exit_tasks() -> None:
    design = _design()
    instruction = practice_prompt_instruction(design)
    approved = design.targets[0]

    assert design.planning_context.learner_level in instruction
    assert design.planning_context.prerequisites[0] in instruction
    assert design.objective in instruction
    assert approved.outcome in instruction
    assert approved.target_invariant in instruction
    assert approved.independent_exit_task not in instruction
    assert approved.delayed_transfer_task not in instruction


def test_canvas_rejects_checkpoint_in_same_path_section_without_approved_anchor() -> None:
    design = _design()
    source = CanvasDocument(
        id="course-lecture",
        course_id="course",
        lecture_id="lecture",
        title="Lecture",
        source_kind="markdown",
        source_ref="lecture-01.md",
        workspace_path="course/index.md",
        sections=[
            _source_section("overview", "This introduction has no approved excerpt."),
            _source_section("evidence", "The cited evidence supports the conclusion."),
        ],
    )
    approved = design.targets[0]
    document = source.model_copy(
        update={
            "source_kind": "generated",
            "sections": [
                source.sections[0].model_copy(
                    update={
                        "source_section_id": "overview",
                        "blocks": [
                            CanvasBlock(
                                id=f"practice-{approved.id}",
                                type="checkpoint",
                                text=approved.baseline_task,
                            )
                        ],
                    }
                ),
                source.sections[1].model_copy(
                    update={"source_section_id": "evidence", "blocks": []}
                ),
            ],
        }
    )

    with pytest.raises(CanvasGenerationRepairableError, match="anchor-bearing source section"):
        validate_practice_candidate(document, design, source_document=source)


def test_canvas_markdown_persists_exact_source_section_identity(tmp_path: Path) -> None:
    document = _generated_document(_design())
    document = document.model_copy(
        update={
            "sections": [document.sections[0].model_copy(update={"source_section_id": "evidence"})]
        }
    )

    write_document_source(document, tmp_path)
    reloaded = read_document_source(tmp_path)

    assert reloaded.sections[0].source_section_id == "evidence"


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
