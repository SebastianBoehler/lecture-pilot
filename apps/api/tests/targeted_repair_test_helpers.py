from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection


def invalid_candidate(source_document: CanvasDocument) -> CanvasDocument:
    detail = (
        "This source-grounded explanation connects the definition to the optimization "
        "procedure, its assumptions, and the practical consequence for model training. "
    )
    first_source = source_document.sections[0]
    second_source = source_document.sections[min(1, len(source_document.sections) - 1)]
    first = CanvasSection(
        id="learning-optimization",
        title="Optimization",
        source_ref=first_source.source_ref or source_document.source_ref,
        source_section_id=first_source.id,
        blocks=[
            CanvasBlock(id="optimization-intro", type="paragraph", text=detail * 2),
            CanvasBlock(
                id="optimization-math",
                type="math",
                text=r"The score is computed as w^\top x.",
            ),
            CanvasBlock(id="optimization-example", type="callout", text=detail * 2),
            CanvasBlock(id="optimization-steps", type="paragraph", text=detail * 2),
            CanvasBlock(
                id="optimization-open-check",
                type="checkpoint",
                text="Explain how the transpose makes the score dimensionally valid.",
            ),
            CanvasBlock(
                id="optimization-check",
                type="quiz",
                text="What does the transpose accomplish?",
                items=["It aligns dimensions", "It removes the weights"],
                answer_index=0,
            ),
        ],
    )
    second = CanvasSection(
        id="learning-summary",
        title="Summary",
        source_ref=second_source.source_ref or source_document.source_ref,
        source_section_id=second_source.id,
        blocks=[
            CanvasBlock(id="summary-1", type="paragraph", text=detail * 2),
            CanvasBlock(id="summary-2", type="paragraph", text=detail * 2),
            CanvasBlock(id="summary-3", type="callout", text=detail * 2),
            CanvasBlock(id="summary-4", type="paragraph", text=detail * 2),
            CanvasBlock(
                id="summary-open-check",
                type="checkpoint",
                text="Explain which vector dimensions must align in the score expression.",
            ),
            CanvasBlock(
                id="summary-quiz",
                type="quiz",
                text="Which expression is dimensionally valid?",
                items=[r"w^\top x", "wx"],
                answer_index=0,
            ),
        ],
    )
    return source_document.model_copy(
        update={
            "source_kind": "generated",
            "source_ref": "Lecture01.tex",
            "sections": [first, second],
        }
    )
