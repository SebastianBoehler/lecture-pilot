from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_repair_prompt import _source_evidence


def test_repair_prompt_uses_every_exact_nested_source_reference() -> None:
    sources = [
        CanvasSection(
            id=f"source-{index}",
            title="Repeated lecture topic",
            source_ref=f"arbitrary/nested/material-{index}.pdf pages {index}–{index + 1}",
            blocks=[
                CanvasBlock(
                    id=f"evidence-{index}",
                    type="paragraph",
                    text=f"Distinct repair evidence {index}.",
                )
            ],
        )
        for index in range(1, 5)
    ]
    source = CanvasDocument(
        id="course-lecture",
        course_id="course",
        lecture_id="lecture",
        title="Lecture",
        source_kind="markdown",
        source_ref="arbitrary nested source bundle",
        workspace_path="source/index.md",
        sections=sources,
    )
    target = CanvasSection(
        id="learning-batch",
        title="Repeated lecture topic",
        source_ref=f"{sources[2].source_ref} | {sources[3].source_ref}",
        blocks=[CanvasBlock(id="claim", type="paragraph", text="Candidate claim.")],
    )

    evidence = _source_evidence(source, target)

    assert "Distinct repair evidence 3." in evidence
    assert "Distinct repair evidence 4." in evidence
    assert "Distinct repair evidence 1." not in evidence
