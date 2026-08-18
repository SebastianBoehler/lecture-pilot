import json

import pytest

from canvas_workspace_fixtures import published_course_canvas
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_planner import CourseCanvasPlanner
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.providers import ProviderRegistry
from test_course_canvas_targeted_repair import _invalid_candidate


async def test_section_repair_normalizes_explanatory_math_without_calling_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner, model = _planner(monkeypatch, [])
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
    replacement = repaired.sections[0].blocks[1]
    assert replacement.id == "optimization-math"
    assert replacement.type == "math"
    assert replacement.text == r"\text{The score is computed as }w^\top x."
    assert model.messages == []


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
    section = candidate.sections[0]
    invalid = section.blocks[1].model_copy(update={"text": r"z=\mu+\epsilon\N(0,1)"})
    candidate = candidate.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={"blocks": [section.blocks[0], invalid, *section.blocks[2:]]}
                ),
                *candidate.sections[1:],
            ]
        }
    )

    repaired = await planner.repair_section(
        source,
        candidate,
        section_id="learning-optimization",
        block_id="optimization-math",
        failure_context="Math block optimization-math uses unsupported command \\N.",
    )

    assert len(model.messages) == 2
    assert (
        "Replace unsupported commands with portable KaTeX commands"
        in model.messages[0][0]["content"]
    )
    assert "exactly this outer shape" in model.messages[0][0]["content"]
    assert '"replace_block"' in model.messages[0][0]["content"]
    assert "unsupported or course-specific" in model.messages[1][-1]["content"]
    assert model.temperatures == [0.4, 0.4]
    repaired_math = next(
        block for block in repaired.sections[0].blocks if block.id == "optimization-math"
    )
    assert repaired_math.text == r"z=\mu+\epsilon"
    first_prompt = model.messages[0][1]["content"]
    assert "Failed section context:" in first_prompt
    assert "optimization-intro" in first_prompt
    assert "This source-grounded explanation connects the definition" not in first_prompt


async def test_section_repair_retries_an_empty_model_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner, model = _planner(
        monkeypatch,
        [
            ModelExecutionError("Course planner returned an empty response."),
            _repair_payload([{"type": "math", "text": r"z=\mu+\epsilon"}]),
        ],
    )
    source = published_course_canvas("targeted-repair", "lecture-01")

    repaired = await planner.repair_section(
        source,
        _invalid_candidate(source),
        section_id="learning-optimization",
        block_id="optimization-math",
        failure_context="The formula is unsupported by the source.",
    )

    assert len(model.messages) == 2
    repaired_math = next(
        block for block in repaired.sections[0].blocks if block.id == "optimization-math"
    )
    assert repaired_math.text == r"z=\mu+\epsilon"


async def test_section_repair_does_not_repeat_exhausted_provider_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    try:
        raise TimeoutError("provider timeout")
    except TimeoutError as cause:
        provider_error = ModelExecutionError("The model provider timed out.")
        provider_error.__cause__ = cause
    planner, model = _planner(monkeypatch, [provider_error])
    source = published_course_canvas("targeted-repair", "lecture-01")

    with pytest.raises(ModelExecutionError, match="timed out"):
        await planner.repair_section(
            source,
            _invalid_candidate(source),
            section_id="learning-optimization",
            block_id="optimization-math",
            failure_context="The formula is unsupported by the source.",
        )

    assert len(model.messages) == 1


async def test_checkpoint_repair_keeps_a_checkpoint_when_model_returns_only_prose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner, model = _planner(
        monkeypatch,
        [
            _repair_payload(
                [
                    {
                        "type": "paragraph",
                        "text": (
                            "The transpose aligns the weight vector with the input vector "
                            "before their scalar score is calculated."
                        ),
                    }
                ]
            )
        ],
    )
    source = published_course_canvas("targeted-repair", "lecture-01")
    candidate = _invalid_candidate(source)
    section = candidate.sections[0]
    valid_math = section.blocks[1].model_copy(update={"text": r"w^\top x"})
    target = section.blocks[4]
    candidate = candidate.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={"blocks": [section.blocks[0], valid_math, *section.blocks[2:]]}
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
        failure_context="Canvas quality review failed: the checkpoint is unsupported.",
    )

    repaired_target = next(block for block in repaired.sections[0].blocks if block.id == target.id)
    assert repaired_target.type == "checkpoint"
    assert "transpose aligns" in (repaired_target.text or "")
    assert len(model.messages) == 1


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


async def test_full_planner_automatically_repairs_an_invalid_generated_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    source = published_course_canvas("targeted-repair", "lecture-01")
    source = source.model_copy(
        update={
            "sections": [
                source.sections[0],
                source.sections[0].model_copy(update={"id": "summary", "title": "Summary"}),
            ]
        }
    )
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
    model = _SectionModel(
        {
            "intro": candidate.sections[0].model_dump(),
            "summary": candidate.sections[1].model_dump(),
        },
        repair_payload=_repair_payload([{"type": "math", "text": r"z=\mu+\epsilon"}]),
    )
    planner = CourseCanvasPlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=model,
        quality_reviewer=_NoIssuesQualityReviewer(),
    )

    document = await planner.plan_canvas(source)

    assert model.repair_calls == 1
    assert [section.id for section in document.sections] == [
        "learning-optimization",
        "learning-summary",
    ]
    repaired_math = document.sections[0].blocks[1]
    assert repaired_math.id == "learning-optimization-math-1"
    assert repaired_math.text == r"z=\mu+\epsilon"
    assert (
        document.sections[1].blocks[0].text == (candidate.sections[1].blocks[0].text or "").strip()
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

    assert model.messages == []
    assert caught.value.section_id == "learning-summary"
    assert caught.value.block_id == "summary-2"
    assert caught.value.candidate is not None
    first_math = next(
        block
        for block in caught.value.candidate.sections[0].blocks
        if block.id == "optimization-math"
    )
    assert first_math.text == r"\text{The score is computed as }w^\top x."


class _RepairModel:
    def __init__(self, payloads: list[dict | Exception]) -> None:
        self.payloads = payloads
        self.messages: list[list[dict[str, str]]] = []
        self.temperatures: list[float] = []

    async def complete_plan(self, *, settings, messages, temperature=0.2, response_format=None):
        assert settings.model == "gemini/test-model"
        self.messages.append(messages)
        self.temperatures.append(temperature)
        payload = self.payloads[len(self.messages) - 1]
        if isinstance(payload, Exception):
            raise payload
        return _repair_patch(payload, messages) if response_format else payload


class _NoIssuesQualityReviewer:
    async def review(self, **_kwargs) -> list:
        return []

    async def validate(self, **_kwargs) -> None:
        return None


class _SectionModel:
    def __init__(self, sections: dict[str, dict], *, repair_payload: dict) -> None:
        self.sections = sections
        self.repair_payload = repair_payload
        self.repair_calls = 0

    async def complete_plan(self, *, settings, messages, temperature=0.2, response_format=None):
        if temperature == 0.4:
            self.repair_calls += 1
            return _repair_patch(self.repair_payload, messages)
        evidence = messages[1]["content"]
        source_id = evidence.split("Required section id: ", 1)[1].splitlines()[0]
        return {"title": "Candidate", "sections": [self.sections[source_id]]}


def _planner(
    monkeypatch: pytest.MonkeyPatch,
    payloads: list[dict | Exception],
) -> tuple[CourseCanvasPlanner, _RepairModel]:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    model = _RepairModel(payloads)
    return (
        CourseCanvasPlanner(
            provider_registry=ProviderRegistry.from_env("gemini/test-model"),
            model_client=model,
            quality_reviewer=_NoIssuesQualityReviewer(),
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


def _repair_patch(payload: dict, messages: list[dict[str, str]]) -> dict:
    content = messages[1]["content"]
    section = json.loads(
        content.split("Failed section context:\n", 1)[1].split("\n\nFailed block:", 1)[0]
    )
    block = json.loads(
        content.split("Failed block:\n", 1)[1].split("\n\nRelevant professor source evidence:", 1)[
            0
        ]
    )
    return {
        "edits": [
            {
                "operation": "replace_block",
                "section_id": section["id"],
                "block_id": block["id"],
                "blocks": payload["sections"][0]["blocks"],
            }
        ]
    }
