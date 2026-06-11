from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_enrichment import enrich_learning_document
from lecturepilot.course_canvas_validation import validate_planned_document


def test_enrichment_completes_thin_sections_before_validation() -> None:
    document = CanvasDocument(
        id="demo-lecture",
        course_id="demo-course",
        lecture_id="lecture-01",
        title="Demo lecture",
        source_kind="generated",
        source_ref="uploaded bundle",
        workspace_path="course-planner/lecture-01/source.json",
        sections=[
            CanvasSection(
                id=f"topic-{index}",
                title=f"Topic {index}",
                source_ref=f"source frame {index}",
                blocks=[
                    CanvasBlock(
                        id=f"topic-{index}-p-1",
                        type="paragraph",
                        text="Posterior risk connects evidence with a decision threshold.",
                    )
                ],
            )
            for index in range(1, 6)
        ],
    )

    enriched = enrich_learning_document(document)

    source = document.model_copy(
        update={
            "sections": [
                section.model_copy(update={"id": f"source-{section.id}"})
                for section in document.sections
            ]
        }
    )
    validate_planned_document(enriched, source)
    assert all(len([block for block in section.blocks if block.type != "quiz"]) >= 4 for section in enriched.sections)
    assert any(block.type == "checkpoint" for section in enriched.sections for block in section.blocks)
    assert any(block.type == "quiz" for section in enriched.sections for block in section.blocks)
