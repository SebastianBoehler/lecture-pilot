import json
import sys
from types import SimpleNamespace

import pytest

from canvas_workspace_fixtures import published_course_canvas
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_math import normalize_generated_math, validate_section_math
from lecturepilot.course_canvas_planner import LiteLLMCoursePlanClient
from lecturepilot.providers import ProviderRegistry
from test_course_canvas_section_repair import _planner, _repair_payload
from test_course_canvas_math import _section_with_math
from test_course_canvas_targeted_repair import _invalid_candidate


def test_generated_math_normalization_removes_stray_display_delimiters() -> None:
    formula = r"\begin{aligned}a &= b \\ \[c &= d\end{aligned}"

    normalized = normalize_generated_math(formula)

    assert normalized == r"\begin{aligned}a &= b \\ c &= d\end{aligned}"
    validate_section_math(_section_with_math(normalized))


async def test_course_plan_client_applies_repair_temperature(monkeypatch) -> None:
    calls = []
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        choice = SimpleNamespace(
            finish_reason="stop",
            message=SimpleNamespace(content=json.dumps({"title": "T", "sections": []})),
        )
        return SimpleNamespace(choices=[choice])

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))

    await LiteLLMCoursePlanClient().complete_plan(
        settings=ProviderRegistry.from_env("gemini/test-model").require_ready([]),
        messages=[{"role": "user", "content": "Repair"}],
        temperature=0.3,
    )

    assert calls[0]["temperature"] == 0.3


async def test_section_repair_normalizes_redundant_math_without_calling_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner, model = _planner(monkeypatch, [])
    source = published_course_canvas("targeted-repair", "lecture-01")
    candidate = _invalid_candidate(source)
    section = candidate.sections[0]
    target = section.blocks[1].model_copy(update={"text": r"w^\prime \[x"})
    candidate = candidate.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={"blocks": [section.blocks[0], target, *section.blocks[2:]]}
                ),
                *candidate.sections[1:],
            ]
        }
    )

    repaired = await planner.repair_section(
        source,
        candidate,
        section_id=section.id,
        block_id=target.id,
        failure_context="Math block contains display delimiters.",
    )

    repaired_target = next(block for block in repaired.sections[0].blocks if block.id == target.id)
    assert repaired_target.text == r"w^\prime x"
    assert model.messages == []


async def test_block_repair_rejects_an_oversized_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oversized = _repair_payload(
        [{"type": "paragraph", "text": f"Unrelated rewrite {index}."} for index in range(4)]
    )
    planner, _model = _planner(monkeypatch, [oversized, oversized])
    source = published_course_canvas("targeted-repair", "lecture-01")

    with pytest.raises(CanvasGenerationRepairableError, match="at most 3 replacement blocks"):
        await planner.repair_section(
            source,
            _invalid_candidate(source),
            section_id="learning-optimization",
            block_id="optimization-math",
            failure_context="Repair only the failed formula.",
        )
