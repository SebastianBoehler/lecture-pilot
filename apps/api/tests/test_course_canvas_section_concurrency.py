from __future__ import annotations

import asyncio

import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_planner import CourseCanvasPlanner
from lecturepilot.course_canvas_section_planner import plan_sections_individually
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import ProviderSettings
from lecturepilot.providers import ProviderRegistry


async def test_section_planner_queues_every_source_section_and_keeps_source_order() -> None:
    client = _ConcurrentPlanClient()

    planned = await asyncio.wait_for(
        plan_sections_individually(
            model_client=client,
            settings=_settings(),
            source_document=_source_document(6),
        ),
        timeout=1,
    )

    assert client.max_active == 6
    assert [section.id for section in planned.sections] == [
        f"learning-source-{index}" for index in range(1, 7)
    ]


async def test_section_planner_keeps_a_complete_candidate_after_one_section_fails() -> None:
    client = _OneInvalidSectionClient()

    with pytest.raises(CanvasGenerationRepairableError) as caught:
        await plan_sections_individually(
            model_client=client,
            settings=_settings(),
            source_document=_source_document(4),
        )

    assert set(client.source_ids) == {f"source-{index}" for index in range(1, 5)}
    assert caught.value.section_id == "learning-source-2"
    assert caught.value.block_id == "learning-source-2-math-1"
    assert caught.value.candidate is not None
    assert [section.id for section in caught.value.candidate.sections] == [
        f"learning-source-{index}" for index in range(1, 5)
    ]


async def test_section_planner_retries_an_empty_model_response() -> None:
    client = _TransientSectionPlanClient()

    planned = await plan_sections_individually(
        model_client=client,
        settings=_settings(),
        source_document=_source_document(1),
    )

    assert client.calls == 2
    assert planned.sections[0].id == "learning-source-1"


async def test_section_planner_repairs_an_invalid_checkpoint_before_batch_validation() -> None:
    client = _InvalidCheckpointClient()

    planned = await plan_sections_individually(
        model_client=client,
        settings=_settings(),
        source_document=_source_document(1),
    )

    assert client.calls == 2
    assert "options that are not stated" in client.repair_message
    checkpoint = next(block for block in planned.sections[0].blocks if block.type == "checkpoint")
    assert checkpoint.text == "Explain why predicting a continuous target is a regression task."


async def test_section_planner_repairs_a_section_without_an_open_response_check() -> None:
    client = _QuizOnlySectionClient()

    planned = await plan_sections_individually(
        model_client=client,
        settings=_settings(),
        source_document=_source_document(1),
    )

    assert client.calls == 2
    assert "open-response checkpoint" in client.repair_message
    assert any(block.type == "checkpoint" for block in planned.sections[0].blocks)


async def test_course_planner_starts_with_the_bounded_section_outline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = _SectionOnlyPlanClient()
    planner = CourseCanvasPlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=client,
        quality_reviewer=_NoIssuesQualityReviewer(),
    )

    planned = await planner.plan_canvas(_source_document(4))

    assert client.source_ids == [f"source-{index}" for index in range(1, 5)]
    assert len(planned.sections) == 4


class _ConcurrentPlanClient:
    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self.release = asyncio.Event()

    async def complete_plan(self, *, settings, messages):
        source_id = _source_id(messages)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        if self.active == 6:
            self.release.set()
        await self.release.wait()
        self.active -= 1
        return _section_payload(source_id)


class _OneInvalidSectionClient:
    def __init__(self) -> None:
        self.source_ids: list[str] = []

    async def complete_plan(self, *, settings, messages):
        source_id = _source_id(messages)
        self.source_ids.append(source_id)
        if source_id == "source-2":
            return _section_payload(source_id, math=r"x=\coursemacro{y}")
        return _section_payload(source_id)


class _SectionOnlyPlanClient:
    def __init__(self) -> None:
        self.source_ids: list[str] = []

    async def complete_plan(self, *, settings, messages):
        source_id = _source_id(messages)
        self.source_ids.append(source_id)
        return _section_payload(source_id)


class _TransientSectionPlanClient:
    def __init__(self) -> None:
        self.calls = 0

    async def complete_plan(self, *, settings, messages):
        self.calls += 1
        if self.calls == 1:
            raise ModelExecutionError("Course planner returned an empty response.")
        return _section_payload(_source_id(messages))


class _InvalidCheckpointClient:
    def __init__(self) -> None:
        self.calls = 0
        self.repair_message = ""

    async def complete_plan(self, *, settings, messages):
        self.calls += 1
        if self.calls == 1:
            payload = _section_payload(_source_id(messages))
            payload["sections"][0]["blocks"][-1]["text"] = (
                "Which task is a regression problem because its target is continuous?"
            )
            return payload
        self.repair_message = messages[-1]["content"]
        payload = _section_payload(_source_id(messages))
        payload["sections"][0]["blocks"][-1]["text"] = (
            "Explain why predicting a continuous target is a regression task."
        )
        return payload


class _QuizOnlySectionClient:
    def __init__(self) -> None:
        self.calls = 0
        self.repair_message = ""

    async def complete_plan(self, *, settings, messages):
        self.calls += 1
        payload = _section_payload(_source_id(messages))
        if self.calls == 1:
            payload["sections"][0]["blocks"][-1] = {
                "type": "quiz",
                "text": "Which description matches the posterior-risk mechanism?",
                "items": ["An unrelated claim.", "The source-backed explanation."],
                "answer_index": 1,
            }
            return payload
        self.repair_message = messages[-1]["content"]
        return payload


def _source_id(messages: list[dict[str, str]]) -> str:
    evidence = messages[1]["content"]
    return evidence.split("Required section id: ", 1)[1].splitlines()[0]


def _section_payload(source_id: str, *, math: str | None = None) -> dict:
    blocks = [
        {
            "type": "paragraph",
            "text": (
                f"The explanation for {source_id} connects the source evidence to a concrete "
                "decision, describes the mechanism, and identifies a useful failure case."
            ),
        }
    ]
    if math:
        blocks.append({"type": "math", "text": math})
    blocks.append(
        {
            "type": "checkpoint",
            "text": (
                f"Explain how the mechanism for {source_id} follows from the evidence and "
                "identify one resulting failure mode."
            ),
        }
    )
    if source_id in {"source-2", "source-4"}:
        blocks.append(
            {
                "type": "quiz",
                "text": f"Which statement correctly describes {source_id}?",
                "items": ["An unrelated claim.", f"The explanation for {source_id}."],
                "answer_index": 1,
            }
        )
    return {
        "sections": [
            {
                "id": f"learning-{source_id}",
                "title": f"Learning {source_id}",
                "source_ref": f"Lecture.tex {source_id}",
                "blocks": blocks,
            }
        ]
    }


class _NoIssuesQualityReviewer:
    async def validate(self, **_kwargs) -> None:
        return None


def _source_document(section_count: int) -> CanvasDocument:
    return CanvasDocument(
        id="course-lecture",
        course_id="course",
        lecture_id="lecture",
        title="Lecture",
        source_kind="latex",
        source_ref="Lecture.tex",
        workspace_path="canvas/index.md",
        sections=[
            CanvasSection(
                id=f"source-{index}",
                title=f"Source topic {index}",
                source_ref=f"Lecture.tex frame {index}",
                blocks=[
                    CanvasBlock(
                        id=f"source-{index}-paragraph",
                        type="paragraph",
                        text=(
                            f"Evidence for source topic {index} explains the mechanism, its "
                            "constraints, and a concrete consequence in sufficient detail."
                        ),
                    )
                ],
            )
            for index in range(1, section_count + 1)
        ],
    )


def _settings() -> ProviderSettings:
    return ProviderSettings(
        provider="test",
        model="test/model",
        api_key_env="TEST_API_KEY",
        capabilities=set(),
    )
