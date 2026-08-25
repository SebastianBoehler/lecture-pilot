import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_planner import CourseCanvasPlanner
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_auto_repair import repair_until_quality_valid
from lecturepilot.course_canvas_prompt import planner_messages
from lecturepilot.course_canvas_repair_prompt import repair_blocks_messages, repair_messages
from lecturepilot.course_canvas_section_prompt import section_messages
from lecturepilot.course_canvas_quality import CanvasQualityIssue
from lecturepilot.course_practice_design_models import PracticeDesign
from lecturepilot.providers import ProviderRegistry
from practice_design_test_helpers import proposal


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("checkpoint_id", "checkpoint_text"),
    [
        ("ordinary-checkpoint", "Derive the conclusion from the given evidence."),
        ("practice-derive-conclusion", "Derive a different conclusion from the given evidence."),
    ],
)
async def test_planner_rejects_candidate_missing_or_mutating_practice_checkpoint(
    monkeypatch: pytest.MonkeyPatch, checkpoint_id: str, checkpoint_text: str
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    source = _source()
    design = _design(source)
    candidate = source.model_copy(
        update={
            "source_kind": "generated",
            "sections": [
                source.sections[0].model_copy(
                    update={
                        "blocks": [
                            CanvasBlock(id="intro", type="paragraph", text="Grounded context."),
                            CanvasBlock(
                                id=checkpoint_id,
                                type="checkpoint",
                                text=checkpoint_text,
                            ),
                        ]
                    }
                )
            ],
        }
    )

    async def plan_sections(**_kwargs):
        return candidate

    monkeypatch.setattr(
        "lecturepilot.course_canvas_planner.plan_sections_individually", plan_sections
    )
    planner = CourseCanvasPlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        quality_reviewer=_NoQualityIssues(),
    )

    with pytest.raises(CanvasGenerationRepairableError):
        await planner.plan_canvas(source, practice_design=design)


def test_initial_section_and_repair_prompts_include_approved_target_contract() -> None:
    source = _source()
    design = _design(source)
    target = design.targets[0]
    section = source.sections[0]
    candidate = source.model_copy(update={"source_kind": "generated"})
    block = CanvasBlock(id=f"practice-{target.id}", type="checkpoint", text=target.baseline_task)

    initial = "\n".join(message["content"] for message in planner_messages(source, design))
    section_prompt = "\n".join(
        message["content"]
        for message in section_messages(
            source, section, practice_design=design, applicable_targets=(target,)
        )
    )
    repair = "\n".join(
        message["content"]
        for message in repair_messages(
            source,
            candidate.sections[0],
            block,
            "A checkpoint needs repair.",
            practice_design=design,
            output_language="en",
        )
    )
    batched = "\n".join(
        message["content"]
        for message in repair_blocks_messages(
            source,
            candidate.sections[0],
            [block, CanvasBlock(id="intro", type="paragraph", text="Grounded context.")],
            "A block needs repair.",
            practice_design=design,
            output_language="en",
        )
    )

    for prompt in (initial, section_prompt, repair, batched):
        assert design.revision in prompt
        assert f"practice-{target.id}" in prompt
        assert target.baseline_task in prompt


@pytest.mark.anyio
async def test_automatic_repair_rejects_a_mutated_canonical_checkpoint() -> None:
    source = _source()
    design = _design(source)
    target = design.targets[0]
    candidate = source.model_copy(
        update={
            "source_kind": "generated",
            "sections": [
                source.sections[0].model_copy(
                    update={
                        "blocks": [
                            CanvasBlock(id="intro", type="paragraph", text="Grounded context."),
                            CanvasBlock(
                                id=f"practice-{target.id}",
                                type="checkpoint",
                                text=target.baseline_task,
                            ),
                        ]
                    }
                )
            ],
        }
    )
    planner = _MutatingRepairPlanner(target.id)

    with pytest.raises(CanvasGenerationRepairableError, match="approved baseline task"):
        await repair_until_quality_valid(
            planner,
            source=source,
            candidate=candidate,
            section_id="source",
            block_id="intro",
            failure_context="Canvas quality review failed.",
            output_language="en",
            practice_design=design,
            quality_issues=[
                CanvasQualityIssue(section_id="source", block_id="intro", reason="Fix.")
            ],
        )

    assert planner.received_designs == [design]


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
                blocks=[CanvasBlock(id="source-text", type="paragraph", text="Grounded context.")],
            )
        ],
    )


def _design(source: CanvasDocument):
    draft = proposal()
    target = draft.targets[0].model_copy(
        update={
            "baseline_task": "Derive the conclusion from the stated evidence and justify it.",
            "independent_exit_task": "Derive a conclusion from parallel evidence and justify it.",
            "delayed_transfer_task": "Derive a conclusion after details change and justify it.",
            "source_refs": ("lecture.md",),
        }
    )
    return PracticeDesign.create(
        course_id=source.course_id,
        lecture_id=source.lecture_id,
        lecture_title=source.title,
        objective=draft.objective,
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
