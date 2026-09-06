import pytest

from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.course_canvas_auto_repair import repair_until_quality_valid
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_planner import CourseCanvasPlanner
from lecturepilot.course_canvas_validation import validate_planned_document
from lecturepilot.providers import ProviderRegistry
from test_course_canvas_batched_repair import _documents


async def test_repairs_next_invalid_block_without_discarding_successful_patch(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    source, candidate, design = _documents()
    for index, section in enumerate(candidate.sections):
        section.blocks.append(CanvasBlock(id=f"bad-{index}", type="math", text=r"\custom{x}"))
    model = _MathPatchModel()
    planner = CourseCanvasPlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=model,
        quality_reviewer=_NoIssues(),
    )
    with pytest.raises(CanvasGenerationRepairableError) as caught:
        validate_planned_document(candidate, source)

    repaired = await repair_until_quality_valid(
        planner,
        source=source,
        candidate=candidate,
        section_id=caught.value.section_id,
        block_id=caught.value.block_id,
        failure_context=str(caught.value),
        output_language="en",
        practice_design=design,
    )

    validate_planned_document(repaired, source)
    assert model.targets == ["bad-0", "bad-1"]
    assert all(s.blocks[-1].text == "x" for s in repaired.sections)


class _MathPatchModel:
    def __init__(self):
        self.targets = []

    async def complete_plan(self, *, response_format, **kwargs):
        fields = response_format["json_schema"]["schema"]["properties"]["edits"]["items"][
            "properties"
        ]
        block_id = fields["block_id"]["enum"][0]
        self.targets.append(block_id)
        return {
            "edits": [
                {
                    "operation": "replace_block",
                    "section_id": fields["section_id"]["enum"][0],
                    "block_id": block_id,
                    "blocks": [{"type": "math", "text": "x"}],
                }
            ]
        }


class _NoIssues:
    async def review(self, **kwargs):
        return []
