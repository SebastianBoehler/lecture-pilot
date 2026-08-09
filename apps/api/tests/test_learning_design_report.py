from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_learning_design_store import canvas_digest
from lecturepilot.learning_map import LearningMapGate, build_learning_map


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
        "covered": 2,
        "total": 2,
        "status": "complete",
    }
    assert first.coverage.transfer_prompts.model_dump() == {
        "covered": 1,
        "total": 1,
        "status": "complete",
    }
    assert first.concepts[0].source_backed_assessment_ids == [
        "mechanism-check",
        "mechanism-quiz",
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
    assert gateful.coverage.transfer_prompts.covered == gateful.coverage.transfer_prompts.total == 1
    assert no_gate.coverage.transfer_prompts.model_dump() == {
        "covered": 0,
        "total": 0,
        "status": "not_applicable",
    }
    assert [item.code for item in no_gate.diagnostics] == ["quiz_only_no_open_checkpoint"]


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
        "covered": 0,
        "total": 2,
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
    assert any(item.code == "no_source_backed_assessment" for item in report.diagnostics)


def test_report_identifies_unassessed_concepts_late_examples_and_linear_prerequisites() -> None:
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
    prerequisite = by_code["inferred_linear_prerequisite"]
    assert prerequisite.coordinates.section_id == "second"
    assert prerequisite.coordinates.prerequisite_section_id == "first"
    assert all(item.id.startswith(f"{item.code}:") for item in report.diagnostics)


def _report(document: CanvasDocument):
    try:
        from lecturepilot.learning_design_report import build_learning_design_report
    except ModuleNotFoundError:
        pytest.fail("learning-design report module is missing", pytrace=False)
    learning_map = build_learning_map(document)
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
