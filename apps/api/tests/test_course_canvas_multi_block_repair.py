import pytest

from lecturepilot.course_canvas_planner import CourseCanvasPlanner
from lecturepilot.course_canvas_repair_apply import apply_replacement
from lecturepilot.course_canvas_practice_contract import validate_practice_candidate
from lecturepilot.providers import ProviderRegistry
from test_course_canvas_batched_repair import _documents


def test_checkpoint_repair_can_add_explanation_without_claiming_another_practice_target():
    source, candidate, design = _documents()
    original = next(
        s for s in candidate.sections if any(b.id.startswith("practice-") for b in s.blocks)
    )
    target = next(b for b in original.blocks if b.id.startswith("practice-"))
    replacement = original.model_copy(
        update={
            "blocks": [
                target.model_copy(update={"type": "paragraph", "text": "Supporting explanation."}),
                target,
            ]
        }
    )

    repaired = apply_replacement(candidate, original, replacement, target)

    validate_practice_candidate(repaired, design, source_document=source)
    assert any(b.text == "Supporting explanation." for s in repaired.sections for b in s.blocks)
    assert sum(b.id == target.id for s in repaired.sections for b in s.blocks) == 1


async def test_multi_block_repair_applies_one_atomic_patch_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    source, candidate, design = _documents()
    section = candidate.sections[0]
    targets = [section.blocks[0], section.blocks[2]]
    replacements = [
        target.model_copy(update={"text": f"{target.text} Corrected."}) for target in targets
    ]
    model = _MultiPatchModel(section.id, replacements)
    planner = CourseCanvasPlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=model,
    )

    repaired = await planner.repair_blocks(
        source,
        candidate,
        section_id=section.id,
        block_ids=[target.id for target in targets],
        failure_context="Canvas quality review failed: fix both reported issues.",
        output_language="en",
        practice_design=design,
    )

    assert model.calls == 1
    repaired_section = repaired.sections[0]
    assert [block.id for block in repaired_section.blocks] == [block.id for block in section.blocks]
    assert repaired_section.blocks[0].text == replacements[0].text
    assert repaired_section.blocks[2].text == replacements[1].text
    assert repaired_section.blocks[1] == section.blocks[1]
    assert repaired.sections[1] == candidate.sections[1]


def test_repair_generated_block_ids_do_not_collide_with_other_sections() -> None:
    _source, candidate, _design = _documents()
    first = candidate.sections[0]
    target = first.blocks[0]
    candidate.sections[1].blocks[0] = (
        candidate.sections[1].blocks[0].model_copy(update={"id": f"{target.id}-repair-1"})
    )
    replacement = first.model_copy(
        update={
            "blocks": [
                target.model_copy(update={"type": "callout"}),
                target.model_copy(update={"text": "Corrected."}),
            ]
        }
    )

    repaired = apply_replacement(candidate, first, replacement, target)

    ids = [block.id for section in repaired.sections for block in section.blocks]
    assert len(ids) == len(set(ids))
    assert f"{target.id}-repair-1-2" in ids


class _MultiPatchModel:
    def __init__(self, section_id, replacements) -> None:
        self.section_id = section_id
        self.replacements = replacements
        self.calls = 0

    async def complete_plan(self, **_kwargs):
        self.calls += 1
        return {
            "edits": [
                {
                    "operation": "replace_block",
                    "section_id": self.section_id,
                    "block_id": replacement.id,
                    "blocks": [replacement.model_dump()],
                }
                for replacement in self.replacements
            ]
        }
