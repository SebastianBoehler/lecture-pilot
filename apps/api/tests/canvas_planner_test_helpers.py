from lecturepilot.canvas_models import CanvasBlock, CanvasDocument
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError


class RepairingCoursePlanner:
    def __init__(self) -> None:
        self.repair_contexts: list[str | None] = []

    async def plan_canvas(
        self,
        source_document: CanvasDocument,
        *,
        practice_design,
        repair_context: str | None = None,
        output_language: str,
    ) -> CanvasDocument:
        self.repair_contexts.append(repair_context)
        if repair_context is None:
            raise CanvasGenerationRepairableError(
                "Math block risk-equation uses unsupported command \\P."
            )
        first = source_document.sections[0]
        return source_document.model_copy(
            update={
                "source_kind": "generated",
                "source_ref": "Repaired from source evidence",
                "sections": [
                    first.model_copy(
                        update={
                            "blocks": [
                                *first.blocks,
                                CanvasBlock(
                                    id=f"practice-{practice_design.targets[0].id}",
                                    type="checkpoint",
                                    text=practice_design.targets[0].baseline_task,
                                ),
                            ]
                        }
                    ),
                    *source_document.sections[1:],
                ],
            }
        )


class RecordingFallbackPlanClient:
    def __init__(self) -> None:
        self.source_ids: list[str] = []

    async def complete_plan(self, *, settings, messages):
        evidence = messages[1]["content"]
        source_id = evidence.split("Required section id: ", 1)[1].splitlines()[0]
        self.source_ids.append(source_id)
        return {
            "sections": [
                {
                    "id": f"learning-{source_id}",
                    "title": f"Learning {source_id}",
                    "source_ref": f"Lecture.tex {source_id}",
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text": "A source-grounded explanation of this learning topic.",
                        },
                        {
                            "type": "checkpoint",
                            "text": (
                                "Explain how this learning topic follows from the evidence "
                                "and identify one consequence."
                            ),
                        },
                    ],
                }
            ]
        }
