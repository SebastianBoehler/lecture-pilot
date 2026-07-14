from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_prompt import MAX_SOURCE_EVIDENCE_CHARS, source_evidence


def test_source_evidence_reserves_detail_for_late_outline_sections() -> None:
    early_blocks = [
        CanvasBlock(
            id=f"early-{index}",
            type="paragraph",
            text=(f"Early detail {index}. " + "dense evidence " * 300).strip(),
        )
        for index in range(60)
    ]
    sections = [
        CanvasSection(
            id="early",
            title="Large early section",
            source_ref="frames 1-60",
            blocks=early_blocks,
        ),
        *[
            CanvasSection(
                id=f"later-{index}",
                title=f"Later topic {index}",
                source_ref=f"frame {60 + index}",
                blocks=[
                    CanvasBlock(
                        id=f"later-{index}-detail",
                        type="paragraph",
                        text=f"LATE-EVIDENCE-{index} explains a distinct later concept.",
                    )
                ],
            )
            for index in range(1, 12)
        ],
    ]
    document = CanvasDocument(
        id="course-lecture",
        course_id="course",
        lecture_id="lecture",
        title="Lecture",
        source_kind="latex",
        source_ref="Lecture.tex",
        workspace_path="canvas/index.md",
        sections=sections,
    )

    evidence = source_evidence(document)

    assert len(evidence) <= MAX_SOURCE_EVIDENCE_CHARS
    assert "Early detail 0" in evidence
    for index in range(1, 12):
        assert f"LATE-EVIDENCE-{index}" in evidence
