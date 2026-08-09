from __future__ import annotations

import hashlib
import json

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.learning_design_report_models import (
    DiagnosticCode,
    LearningDesignConceptReport,
    LearningDesignCoverage,
    LearningDesignCoverageSummary,
    LearningDesignDiagnostic,
    LearningDesignDiagnosticCoordinates,
    LearningDesignReport,
    LearningDesignSummary,
)
from lecturepilot.learning_map import LearningMap, LearningMapNode
from lecturepilot.quiz_identity import canonical_quiz_id, is_quiz_block


def build_learning_design_report(
    *,
    document: CanvasDocument,
    learning_map: LearningMap,
    draft_digest: str,
    source_revision: str,
) -> LearningDesignReport:
    nodes = {node.section_id: node for node in learning_map.nodes}
    sections = {section.id: section for section in document.sections}
    if (
        document.course_id != learning_map.course_id
        or document.lecture_id != learning_map.lecture_id
        or set(sections) != set(nodes)
    ):
        raise ValueError("Learning-design report inputs do not describe the same draft.")

    concepts: list[LearningDesignConceptReport] = []
    diagnostics: list[LearningDesignDiagnostic] = []
    source_backed_count = 0
    assessment_count = 0
    previous_section_id: str | None = None
    for section in document.sections:
        node = nodes[section.id]
        concept, concept_diagnostics = _concept_report(
            section=section,
            node=node,
            previous_section_id=previous_section_id,
        )
        concepts.append(concept)
        diagnostics.extend(concept_diagnostics)
        source_backed_count += len(concept.source_backed_assessment_ids)
        assessment_count += len(concept.gate_ids) + len(concept.quiz_ids)
        previous_section_id = section.id

    if source_backed_count == 0:
        diagnostics.append(
            _diagnostic(
                "no_source_backed_assessment",
                "This draft has no source-backed assessment.",
                "Add a checkpoint or quiz to a section with its own source reference.",
            )
        )
    concepts.sort(key=lambda concept: concept.section_id)
    diagnostics.sort(key=_diagnostic_sort_key)
    gate_count = sum(bool(concept.gate_ids) for concept in concepts)
    quiz_count = sum(bool(concept.quiz_ids) for concept in concepts)
    assessed_count = sum(bool(concept.gate_ids or concept.quiz_ids) for concept in concepts)
    transfer_count = sum(bool(gate.transfer_prompt.strip()) for gate in learning_map.gates)
    return LearningDesignReport.create(
        schema_version=1,
        draft_digest=draft_digest,
        source_revision=source_revision,
        learning_map_revision=learning_map.revision,
        summary=LearningDesignSummary(
            total_concepts=len(concepts),
            concepts_with_gate=gate_count,
            concepts_with_quiz=quiz_count,
            concepts_with_assessment=assessed_count,
        ),
        coverage=LearningDesignCoverageSummary(
            gate_concepts=_coverage(gate_count, len(concepts)),
            quiz_concepts=_coverage(quiz_count, len(concepts)),
            source_backed_assessments=_coverage(source_backed_count, assessment_count),
            transfer_prompts=_coverage(transfer_count, len(learning_map.gates)),
        ),
        concepts=concepts,
        diagnostics=diagnostics,
    )


def _concept_report(
    *, section: CanvasSection, node: LearningMapNode, previous_section_id: str | None
) -> tuple[LearningDesignConceptReport, list[LearningDesignDiagnostic]]:
    gate_ids = sorted(node.gate_ids)
    quiz_ids = sorted(node.quiz_ids)
    assessment_ids = sorted([*gate_ids, *quiz_ids])
    local_source = bool(section.source_ref and section.source_ref.strip())
    source_backed = assessment_ids if local_source else []
    diagnostics: list[LearningDesignDiagnostic] = []
    if not assessment_ids:
        diagnostics.append(
            _diagnostic(
                "concept_without_assessment",
                f"{section.title} has no checkpoint or quiz.",
                "Add a source-backed checkpoint or quiz to this section.",
                section_id=section.id,
            )
        )
    if assessment_ids and not local_source:
        for assessment_id in assessment_ids:
            diagnostics.append(
                _diagnostic(
                    "assessment_section_source_missing",
                    f"Assessment {assessment_id} has no local section source reference.",
                    "Add a section-level source reference for this assessment.",
                    section_id=section.id,
                    assessment_id=assessment_id,
                )
            )
    if quiz_ids and not gate_ids:
        diagnostics.append(
            _diagnostic(
                "quiz_only_no_open_checkpoint",
                f"{section.title} has a quiz but no open-answer checkpoint.",
                "Add an open-answer checkpoint that requires the learner to explain their reasoning.",
                section_id=section.id,
            )
        )
    diagnostics.extend(_worked_example_diagnostics(section))
    if previous_section_id and previous_section_id in node.prerequisites:
        diagnostics.append(
            _diagnostic(
                "inferred_linear_prerequisite",
                f"{section.title} initially depends on the preceding section.",
                "Confirm that this inferred prerequisite reflects the intended concept sequence.",
                section_id=section.id,
                prerequisite_section_id=previous_section_id,
            )
        )
    return (
        LearningDesignConceptReport(
            section_id=section.id,
            title=section.title,
            gate_ids=gate_ids,
            quiz_ids=quiz_ids,
            source_backed_assessment_ids=source_backed,
        ),
        diagnostics,
    )


def _worked_example_diagnostics(section: CanvasSection) -> list[LearningDesignDiagnostic]:
    first = next(
        (
            (index, _assessment_id(block))
            for index, block in enumerate(section.blocks)
            if _is_assessment(block)
        ),
        None,
    )
    if first is None:
        return []
    first_index, assessment_id = first
    return [
        _diagnostic(
            "worked_example_after_assessment",
            f"Worked example {block.id} appears after the first assessment.",
            "Move the explicit worked example before the first checkpoint or quiz, or remove its worked-example marker.",
            section_id=section.id,
            assessment_id=assessment_id,
            block_id=block.id,
        )
        for index, block in enumerate(section.blocks)
        if index > first_index and block.id.startswith("worked-example-")
    ]


def _is_assessment(block: CanvasBlock) -> bool:
    return block.type == "checkpoint" or is_quiz_block(block)


def _assessment_id(block: CanvasBlock) -> str:
    return block.id if block.type == "checkpoint" else canonical_quiz_id(block)


def _coverage(covered: int, total: int) -> LearningDesignCoverage:
    status = "not_applicable" if total == 0 else "complete" if covered == total else "incomplete"
    return LearningDesignCoverage(covered=covered, total=total, status=status)


def _diagnostic(
    code: DiagnosticCode,
    message: str,
    action: str,
    *,
    section_id: str | None = None,
    assessment_id: str | None = None,
    block_id: str | None = None,
    prerequisite_section_id: str | None = None,
) -> LearningDesignDiagnostic:
    coordinates = LearningDesignDiagnosticCoordinates(
        section_id=section_id,
        assessment_id=assessment_id,
        block_id=block_id,
        prerequisite_section_id=prerequisite_section_id,
    )
    canonical = json.dumps(
        {"code": code, "coordinates": coordinates.model_dump(mode="json")},
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    identifier = f"{code}:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
    return LearningDesignDiagnostic(
        id=identifier,
        code=code,
        message=message,
        action=action,
        coordinates=coordinates,
    )


def _diagnostic_sort_key(item: LearningDesignDiagnostic) -> tuple[str, ...]:
    coordinates = item.coordinates
    return (
        item.code,
        coordinates.section_id or "",
        coordinates.assessment_id or "",
        coordinates.block_id or "",
        coordinates.prerequisite_section_id or "",
    )
