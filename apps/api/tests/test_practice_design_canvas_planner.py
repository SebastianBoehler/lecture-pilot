import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_practice_design_models import PracticeDesign
from practice_design_test_helpers import proposal, target as build_target


def test_shared_contract_rejects_practice_id_on_non_checkpoint() -> None:
    source = _source()
    design = _design(source)
    target = design.targets[0]
    document = source.model_copy(
        update={
            "source_kind": "generated",
            "sections": [
                source.sections[0].model_copy(
                    update={
                        "blocks": [
                            CanvasBlock(
                                id=f"practice-{target.id}",
                                type="checkpoint",
                                text=target.baseline_task,
                            ),
                            CanvasBlock(
                                id=f"practice-{target.id}",
                                type="paragraph",
                                text="Duplicate canonical id.",
                            ),
                        ]
                    }
                )
            ],
        }
    )

    with pytest.raises(CanvasGenerationRepairableError, match="only be a checkpoint"):
        from lecturepilot.course_canvas_practice_contract import validate_practice_candidate

        validate_practice_candidate(document, design)


def _source() -> CanvasDocument:
    return CanvasDocument(
        id="course-lecture",
        course_id="course",
        lecture_id="lecture",
        title="Lecture",
        source_kind="markdown",
        source_ref="lecture.md",
        workspace_path="source.json",
        sections=[
            CanvasSection(
                id="source",
                title="Source",
                source_ref="lecture.md",
                blocks=[
                    CanvasBlock(
                        id="source-text", type="paragraph", text="Grounded evidence context."
                    )
                ],
            )
        ],
    )


def _design(source: CanvasDocument):
    draft = proposal()
    target = build_target(
        baseline_task="Derive the conclusion from the stated evidence and justify it.",
        independent_exit_task="Derive a conclusion from parallel evidence and justify it.",
        delayed_transfer_task="Derive a conclusion after details change and justify it.",
        source_refs=("lecture.md",),
    )
    return PracticeDesign.create(
        course_id=source.course_id,
        lecture_id=source.lecture_id,
        lecture_title=source.title,
        objective=draft.objective,
        planning_context=draft.planning_context,
        source_revision="a" * 64,
        targets=(target,),
    )


class _NoQualityIssues:
    async def review(self, **_kwargs) -> list:
        return []


class _MutatingRepairPlanner:
    def __init__(self, target_id: str) -> None:
        self.target_id = target_id
        self.received_designs = []

    async def repair_section(self, _source, candidate, *, practice_design, **_kwargs):
        self.received_designs.append(practice_design)
        section = candidate.sections[0]
        block = next(item for item in section.blocks if item.id == f"practice-{self.target_id}")
        return candidate.model_copy(
            update={
                "sections": [
                    section.model_copy(
                        update={
                            "blocks": [
                                item.model_copy(update={"text": "Derive a changed conclusion."})
                                if item.id == block.id
                                else item
                                for item in section.blocks
                            ]
                        }
                    )
                ]
            }
        )

    async def repair_blocks(self, *_args, **_kwargs):
        raise AssertionError("The single issue must use repair_section.")

    async def review_quality(self, *_args, **_kwargs) -> list:
        return []
