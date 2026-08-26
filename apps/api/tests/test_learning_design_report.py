from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_learning_design_store import canvas_digest
from lecturepilot.course_practice_design_models import PracticeDesign
from lecturepilot.learning_map import LearningMapGate, build_learning_map
from practice_design_test_helpers import practice_design_for_canvas, target as practice_target


def test_valid_report_is_deterministic_and_fully_source_backed() -> None:
    document = _document(
        CanvasSection(
            id="mechanism",
            title="Mechanism",
            source_ref="lecture.md#mechanism",
            blocks=[
                CanvasBlock(id="worked-example-mechanism", type="paragraph", text="Example."),
                CanvasBlock(id="mechanism-check", type="checkpoint", text="Explain it."),
                CanvasBlock(
                    id="mechanism-quiz",
                    type="quiz",
                    text="Which mechanism applies?",
                    items=["A", "B"],
                    answer_index=1,
                ),
            ],
        )
    )

    first = _report(document)
    second = _report(document.model_copy(deep=True))

    assert first.report_revision == second.report_revision
    assert first.summary.model_dump() == {
        "total_concepts": 1,
        "concepts_with_gate": 1,
        "concepts_with_quiz": 1,
        "concepts_with_assessment": 1,
    }
    assert first.coverage.gate_concepts.model_dump() == {
        "covered": 1,
        "total": 1,
        "status": "complete",
    }
    assert first.coverage.source_backed_assessments.model_dump() == {
        "covered": 3,
        "total": 3,
        "status": "complete",
    }
    assert first.coverage.transfer_prompts.model_dump() == {
        "covered": 2,
        "total": 2,
        "status": "complete",
    }
    assert first.concepts[0].source_backed_assessment_ids == [
        "mechanism-check",
        "mechanism-quiz",
        "practice-derive-conclusion",
    ]
    assert first.diagnostics == []


def test_transfer_coverage_preserves_the_strict_learning_map_contract() -> None:
    for missing_transfer in ("", "   "):
        with pytest.raises(ValidationError):
            LearningMapGate.create(
                id="strict-check",
                concept_id="strict",
                title="Strict check",
                prompt="Explain it.",
                evidence_criteria=[
                    {"id": "strict-check", "description": "Explains it.", "required": True}
                ],
                transfer_prompt=missing_transfer,
                review_after_days=2,
                section_id="strict",
                source_ref="lecture.md#strict",
            )

    gateful = _report(
        _document(
            CanvasSection(
                id="strict",
                title="Strict",
                source_ref="lecture.md#strict",
                blocks=[CanvasBlock(id="strict-check", type="checkpoint", text="Explain it.")],
            )
        )
    )
    no_gate = _report(
        _document(
            CanvasSection(
                id="quiz-only",
                title="Quiz only",
                source_ref="lecture.md#quiz",
                blocks=[
                    CanvasBlock(
                        id="quiz-only-check",
                        type="quiz",
                        text="Choose.",
                        items=["A", "B"],
                        answer_index=0,
                    )
                ],
            )
        )
    )

    assert gateful.coverage.transfer_prompts.status == "complete"
    assert gateful.coverage.transfer_prompts.covered == gateful.coverage.transfer_prompts.total == 2
    assert no_gate.coverage.transfer_prompts.model_dump() == {
        "covered": 1,
        "total": 1,
        "status": "complete",
    }
    assert no_gate.diagnostics == []


def test_document_source_does_not_mask_missing_local_assessment_sources() -> None:
    document = _document(
        CanvasSection(
            id="local-source",
            title="Local source",
            source_ref=None,
            blocks=[
                CanvasBlock(id="local-check", type="checkpoint", text="Explain."),
                CanvasBlock(
                    id="local-quiz",
                    type="quiz",
                    text="Choose.",
                    items=["A", "B"],
                    answer_index=0,
                ),
            ],
        )
    )

    report = _report(document)

    assert report.coverage.source_backed_assessments.model_dump() == {
        "covered": 1,
        "total": 3,
        "status": "incomplete",
    }
    assert report.concepts[0].source_backed_assessment_ids == []
    missing = [
        item for item in report.diagnostics if item.code == "assessment_section_source_missing"
    ]
    assert [item.coordinates.assessment_id for item in missing] == [
        "local-check",
        "local-quiz",
    ]


def test_report_identifies_unassessed_concepts_and_late_examples_without_sequence_noise() -> None:
    document = _document(
        CanvasSection(
            id="first",
            title="First",
            source_ref="lecture.md#first",
            blocks=[CanvasBlock(id="first-p", type="paragraph", text="Read.")],
        ),
        CanvasSection(
            id="second",
            title="Second",
            source_ref="lecture.md#second",
            blocks=[
                CanvasBlock(id="second-check", type="checkpoint", text="Explain."),
                CanvasBlock(id="worked-example-late", type="paragraph", text="Late example."),
            ],
        ),
    )

    report = _report(document)
    by_code = {item.code: item for item in report.diagnostics}

    assert by_code["concept_without_assessment"].coordinates.section_id == "first"
    assert by_code["worked_example_after_assessment"].coordinates.block_id == (
        "worked-example-late"
    )
    assert by_code["worked_example_after_assessment"].coordinates.assessment_id == "second-check"
    assert "inferred_linear_prerequisite" not in by_code
    assert all(item.id.startswith(f"{item.code}:") for item in report.diagnostics)


def _report(document: CanvasDocument):
    try:
        from lecturepilot.learning_design_report import build_learning_design_report
    except ModuleNotFoundError:
        pytest.fail("learning-design report module is missing", pytrace=False)
    source_sections = [section for section in document.sections if section.source_ref]
    if not source_sections:
        document = document.model_copy(
            update={
                "sections": [
                    *document.sections,
                    CanvasSection(
                        id="practice-source",
                        title="Practice source",
                        source_ref=document.source_ref,
                        blocks=[],
                    ),
                ]
            }
        )
        source_sections = [document.sections[-1]]
    target_section = source_sections[-1]
    base_design = practice_design_for_canvas(document)
    target_payload = base_design.targets[0].model_dump(mode="json")
    target_payload["source_refs"] = (target_section.source_ref,)
    for field in (
        "outcome_anchor",
        "target_invariant_anchor",
        "baseline_task_anchor",
        "independent_exit_task_anchor",
        "delayed_transfer_task_anchor",
    ):
        target_payload.pop(field)
    practice_design = base_design.model_copy(
        update={"targets": (practice_target(**target_payload),)}
    )
    practice_design = PracticeDesign.create(
        course_id=document.course_id,
        lecture_id=document.lecture_id,
        lecture_title=document.title,
        objective=practice_design.objective,
        planning_context=practice_design.planning_context,
        source_revision="a" * 64,
        targets=practice_design.targets,
    )
    document = document.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={
                        "blocks": [
                            *section.blocks,
                            CanvasBlock(
                                id=f"practice-{practice_design.targets[0].id}",
                                type="checkpoint",
                                text=practice_design.targets[0].baseline_task,
                            ),
                        ]
                    }
                )
                if section.id == target_section.id
                else section
                for section in document.sections
            ]
        }
    )
    learning_map = build_learning_map(document, practice_design)
    return build_learning_design_report(
        document=document,
        learning_map=learning_map,
        draft_digest=canvas_digest(document),
        source_revision="a" * 64,
    )


def _document(*sections: CanvasSection) -> CanvasDocument:
    return CanvasDocument(
        id="course-lecture",
        course_id="course",
        lecture_id="lecture",
        title="Lecture",
        source_kind="generated",
        source_ref="lecture.md",
        workspace_path=str(Path("course") / "index.md"),
        sections=list(sections),
    )
