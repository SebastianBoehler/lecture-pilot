import pytest

from canvas_workspace_fixtures import published_course_canvas
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_planner import CourseCanvasPlanner
from lecturepilot.providers import ProviderRegistry
from test_course_canvas_targeted_repair import _invalid_candidate


async def test_section_repair_applies_only_replacement_blocks_and_preserves_the_rest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner, model = _planner(
        monkeypatch,
        [
            _repair_payload(
                [
                    {
                        "type": "paragraph",
                        "text": "The transpose aligns the weight vector with the input dimensions.",
                    },
                    {"type": "math", "text": r"w^\top x"},
                ]
            )
        ],
    )
    source = published_course_canvas("targeted-repair", "lecture-01")
    candidate = _invalid_candidate(source)

    repaired = await planner.repair_section(
        source,
        candidate,
        section_id="learning-optimization",
        block_id="optimization-math",
        failure_context=(
            "Math block optimization-math in Optimization contains explanatory prose; "
            "move that text to a paragraph or callout block."
        ),
    )

    assert repaired.sections[1] == candidate.sections[1]
    assert repaired.sections[0].blocks[0] == candidate.sections[0].blocks[0]
    assert repaired.sections[0].blocks[-3:] == candidate.sections[0].blocks[-3:]
    replacement = repaired.sections[0].blocks[1:3]
    assert [(block.id, block.type) for block in replacement] == [
        ("optimization-math-repair-1", "paragraph"),
        ("optimization-math", "math"),
    ]
    assert replacement[1].text == r"w^\top x"
    prompt = model.messages[0]
    assert "optimization-math" in prompt[-1]["content"]
    assert "only replacement blocks" in prompt[0]["content"]
    assert "move that text to a paragraph" in prompt[-1]["content"]


async def test_section_repair_retries_once_with_the_new_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner, model = _planner(
        monkeypatch,
        [
            _repair_payload([{"type": "math", "text": r"z=\mu+\epsilon\N(0,1)"}]),
            _repair_payload([{"type": "math", "text": r"z=\mu+\epsilon"}]),
        ],
    )
    source = published_course_canvas("targeted-repair", "lecture-01")
    candidate = _invalid_candidate(source)

    repaired = await planner.repair_section(
        source,
        candidate,
        section_id="learning-optimization",
        block_id="optimization-math",
        failure_context="Math block optimization-math uses unsupported command \\N.",
    )

    assert len(model.messages) == 2
    assert "unsupported or course-specific" in model.messages[1][-1]["content"]
    repaired_math = next(
        block for block in repaired.sections[0].blocks if block.id == "optimization-math"
    )
    assert repaired_math.text == r"z=\mu+\epsilon"


async def test_section_repair_rejects_two_invalid_patches_without_mutating_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = _repair_payload([{"type": "math", "text": r"z=\mu+\epsilon\N(0,1)"}])
    planner, model = _planner(monkeypatch, [invalid, invalid])
    source = published_course_canvas("targeted-repair", "lecture-01")
    candidate = _invalid_candidate(source)
    snapshot = candidate.model_copy(deep=True)

    with pytest.raises(CanvasGenerationRepairableError, match="unsupported or course-specific"):
        await planner.repair_section(
            source,
            candidate,
            section_id="learning-optimization",
            block_id="optimization-math",
            failure_context="Math block optimization-math uses unsupported command \\N.",
        )

    assert len(model.messages) == 2
    assert candidate == snapshot


async def test_full_planner_quarantines_the_invalid_candidate_with_block_coordinates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    source = published_course_canvas("targeted-repair", "lecture-01")
    candidate = _invalid_candidate(source)
    target_section = candidate.sections[0]
    invalid_math = target_section.blocks[1].model_copy(update={"text": r"z=\mu+\epsilon\N(0,1)"})
    candidate = candidate.model_copy(
        update={
            "sections": [
                target_section.model_copy(
                    update={
                        "blocks": [
                            target_section.blocks[0],
                            invalid_math,
                            *target_section.blocks[2:],
                        ]
                    }
                ),
                candidate.sections[1],
            ]
        }
    )
    model = _RepeatingModel(
        {
            "title": candidate.title,
            "sections": [section.model_dump() for section in candidate.sections],
        }
    )
    planner = CourseCanvasPlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=model,
    )

    with pytest.raises(CanvasGenerationRepairableError) as caught:
        await planner.plan_canvas(source)

    assert caught.value.candidate is not None
    assert caught.value.section_id == "learning-optimization"
    assert caught.value.block_id == "optimization-math"
    assert [section.id for section in caught.value.candidate.sections] == [
        "learning-optimization",
        "learning-summary",
    ]
    assert (
        caught.value.candidate.sections[1].blocks[0].text
        == (candidate.sections[1].blocks[0].text or "").strip()
    )


async def test_section_repair_retains_the_patch_and_advances_to_the_next_invalid_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner, model = _planner(
        monkeypatch,
        [_repair_payload([{"type": "math", "text": r"w^\top x"}])],
    )
    source = published_course_canvas("targeted-repair", "lecture-01")
    candidate = _invalid_candidate(source)
    second = candidate.sections[1]
    second_invalid = second.blocks[1].model_copy(
        update={"type": "math", "text": r"z=\mu+\epsilon\N(0,1)"}
    )
    candidate = candidate.model_copy(
        update={
            "sections": [
                candidate.sections[0],
                second.model_copy(
                    update={"blocks": [second.blocks[0], second_invalid, *second.blocks[2:]]}
                ),
            ]
        }
    )

    with pytest.raises(CanvasGenerationRepairableError) as caught:
        await planner.repair_section(
            source,
            candidate,
            section_id="learning-optimization",
            block_id="optimization-math",
            failure_context="The first formula contains explanatory prose.",
        )

    assert len(model.messages) == 1
    assert caught.value.section_id == "learning-summary"
    assert caught.value.block_id == "summary-2"
    assert caught.value.candidate is not None
    first_math = next(
        block
        for block in caught.value.candidate.sections[0].blocks
        if block.id == "optimization-math"
    )
    assert first_math.text == r"w^\top x"


async def test_block_repair_rejects_an_oversized_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner, _model = _planner(
        monkeypatch,
        [
            _repair_payload(
                [{"type": "paragraph", "text": f"Unrelated rewrite {index}."} for index in range(4)]
            ),
            _repair_payload(
                [{"type": "paragraph", "text": f"Unrelated rewrite {index}."} for index in range(4)]
            ),
        ],
    )
    source = published_course_canvas("targeted-repair", "lecture-01")
    candidate = _invalid_candidate(source)

    with pytest.raises(CanvasGenerationRepairableError, match="at most 3 replacement blocks"):
        await planner.repair_section(
            source,
            candidate,
            section_id="learning-optimization",
            block_id="optimization-math",
            failure_context="Repair only the failed formula.",
        )


class _RepairModel:
    def __init__(self, payloads: list[dict]) -> None:
        self.payloads = payloads
        self.messages: list[list[dict[str, str]]] = []

    async def complete_plan(self, *, settings, messages):
        assert settings.model == "gemini/test-model"
        self.messages.append(messages)
        return self.payloads[len(self.messages) - 1]


class _RepeatingModel:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    async def complete_plan(self, *, settings, messages):
        return self.payload


def _planner(
    monkeypatch: pytest.MonkeyPatch,
    payloads: list[dict],
) -> tuple[CourseCanvasPlanner, _RepairModel]:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    model = _RepairModel(payloads)
    return (
        CourseCanvasPlanner(
            provider_registry=ProviderRegistry.from_env("gemini/test-model"),
            model_client=model,
        ),
        model,
    )


def _repair_payload(blocks: list[dict]) -> dict:
    normalized = [
        {
            "id": f"replacement-{index}",
            "type": block["type"],
            "text": block.get("text"),
            "items": [],
            "asset_path": None,
            "caption": None,
            "answer_index": None,
        }
        for index, block in enumerate(blocks, start=1)
    ]
    return {
        "title": "Targeted block repair",
        "sections": [
            {
                "id": "replacement",
                "title": "Targeted block repair",
                "source_ref": "Lecture01.tex frame 1",
                "blocks": normalized,
            }
        ],
    }
