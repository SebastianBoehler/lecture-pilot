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
    assessment_sections = [
        section
        for section in enriched.sections
        if any(block.type in {"checkpoint", "quiz"} for block in section.blocks)
    ]
    quizzes = [block for section in enriched.sections for block in section.blocks if block.type == "quiz"]
    assert [section.id for section in assessment_sections] == ["topic-2", "topic-4", "topic-5"]
    assert len(quizzes) == 2
    assert enriched.sections[-1].blocks[-1].type == "quiz"
    callouts = [
        block.text
        for section in enriched.sections
        for block in section.blocks
        if block.type == "callout"
    ]
    assert all("Learning checkpoint: use" not in text for text in callouts if text)
    assert all("rephrase the section" not in text for text in callouts if text)
    assert any(text and text.startswith("Check yourself:") for text in callouts)
    all_text = "\n".join(
        block.text or "\n".join(block.items)
        for section in enriched.sections
        for block in section.blocks
    )
    assert "turns the source material into a decision step" not in all_text


def test_enrichment_preserves_model_authored_quizzes() -> None:
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
    document.sections[0].blocks.append(
        CanvasBlock(
            id="model-authored-quiz",
            type="quiz",
            caption="Model check",
            text="Which term changes after evidence?",
            items=["Posterior", "Alphabet", "Filename"],
            answer_index=0,
        )
    )

    enriched = enrich_learning_document(document)

    preserved = [block for section in enriched.sections for block in section.blocks if block.id == "model-authored-quiz"]
    assert len(preserved) == 1
    assert preserved[0].text == "Which term changes after evidence?"
