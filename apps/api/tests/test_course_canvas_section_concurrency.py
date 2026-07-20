from __future__ import annotations

import asyncio

import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_planner import CourseCanvasPlanner
from lecturepilot.course_canvas_section_planner import plan_sections_individually
from lecturepilot.models import ProviderSettings
from lecturepilot.providers import ProviderRegistry


async def test_section_planner_runs_three_calls_concurrently_and_keeps_source_order() -> None:
    client = _ConcurrentPlanClient()

    planned = await asyncio.wait_for(
        plan_sections_individually(
            model_client=client,
            settings=_settings(),
            source_document=_source_document(6),
        ),
        timeout=1,
    )

    assert client.max_active == 3
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


async def test_course_planner_starts_with_the_bounded_section_outline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = _SectionOnlyPlanClient()
    planner = CourseCanvasPlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=client,
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
        if self.active == 3:
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
