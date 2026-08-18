from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_evidence_batches import group_evidence_sections
from lecturepilot.course_canvas_quality_prompt import compact_quality_evidence


def test_evidence_batches_keep_specific_refs_for_quality_matching() -> None:
    source_sections = [
        CanvasSection(
            id=f"source-{index}",
            title=f"Source {index}",
            source_ref=f"nested/material-{index}.pdf page {index}",
            blocks=[
                CanvasBlock(
                    id=f"evidence-{index}",
                    type="paragraph",
                    text=f"Distinct evidence {index}.",
                )
            ],
        )
        for index in range(1, 3)
    ]
    broad_document_ref = ("nested/course-source-bundle " * 17).strip()
    source = CanvasDocument(
        id="course-lecture",
        course_id="course",
        lecture_id="lecture",
        title="Lecture",
        source_kind="markdown",
        source_ref=broad_document_ref,
        workspace_path="source/index.md",
        sections=source_sections,
    )

    grouped = group_evidence_sections(
        source.sections,
        max_groups=1,
        document_source_ref=source.source_ref,
    )
    candidate = source.model_copy(update={"source_kind": "generated", "sections": grouped})
    prompt = compact_quality_evidence(source, candidate)

    assert grouped[0].source_ref == ("nested/material-1.pdf page 1 | nested/material-2.pdf page 2")
    assert "Distinct evidence 1." in prompt
    assert "Distinct evidence 2." in prompt


def test_quality_evidence_keeps_component_options_and_selected_answer() -> None:
    source = CanvasDocument(
        id="course-lecture",
        course_id="course",
        lecture_id="lecture",
        title="Lecture",
        source_kind="markdown",
        source_ref="arbitrary/nested/source.md",
        workspace_path="source/index.md",
        sections=[
            CanvasSection(
                id="source",
                title="Source",
                source_ref="arbitrary/nested/source.md",
                blocks=[CanvasBlock(id="fact", type="paragraph", text="Precision uses TP + FP.")],
            )
        ],
    )
    component = CanvasBlock(
        id="precision-choice",
        type="component",
        text="Which denominator defines precision?",
        items=["TP + FP", "TP + FN"],
        answer_index=0,
        component_id="precision-choice",
        component_type="single_choice_quiz",
        component_ref="components/precision-choice.yaml",
        component_version=1,
        option_ids=["a", "b"],
    )
    candidate = source.model_copy(
        update={
            "source_kind": "generated",
            "sections": [source.sections[0].model_copy(update={"blocks": [component]})],
        }
    )

    prompt = compact_quality_evidence(source, candidate)

    assert "options=['TP + FP', 'TP + FN']" in prompt
    assert "selected=0" in prompt
