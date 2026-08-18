from __future__ import annotations

import asyncio

import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_planner import CourseCanvasPlanner
from lecturepilot.course_canvas_section_checkpoints import SectionPlanCheckpointStore
from lecturepilot.course_canvas_section_planner import plan_sections_individually
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import ProviderSettings
from lecturepilot.providers import ProviderRegistry


async def test_dense_section_plan_uses_three_provider_rounds_and_keeps_source_order() -> None:
    client = _ControlledPlanClient()

    generation = asyncio.create_task(
        plan_sections_individually(
            model_client=client,
            settings=_settings(),
            source_document=_source_document(6),
        )
    )
    await client.wait_until_started(2)
    assert client.started == 2
    client.release(2)
    await client.wait_until_started(4)
    assert client.started == 4
    client.release(2)
    await client.wait_until_started(5)
    client.release(1)
    planned = await asyncio.wait_for(generation, timeout=1)

    assert client.max_active == 2
    assert [section.id for section in planned.sections] == [
        f"learning-evidence-batch-{index}" for index in range(1, 6)
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

    assert client.calls == 1
    checkpoint = next(block for block in planned.sections[0].blocks if block.type == "checkpoint")
    assert checkpoint.text.startswith("Explain this statement")


async def test_section_planner_repairs_a_section_without_an_open_response_check() -> None:
    client = _QuizOnlySectionClient()

    planned = await plan_sections_individually(
        model_client=client,
        settings=_settings(),
        source_document=_source_document(1),
    )

    assert client.calls == 1
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


async def test_dense_lecture_is_grouped_into_five_learning_sections() -> None:
    client = _SectionOnlyPlanClient()

    planned = await plan_sections_individually(
        model_client=client,
        settings=_settings(),
        source_document=_source_document(14),
    )

    assert len(client.source_ids) == 5
    assert len(planned.sections) == 5
    assert client.source_ids == [f"evidence-batch-{index}" for index in range(1, 6)]


async def test_generated_section_provenance_comes_from_supplied_evidence() -> None:
    planned = await plan_sections_individually(
        model_client=_SectionOnlyPlanClient(),
        settings=_settings(),
        source_document=_source_document(1),
    )

    assert planned.sections[0].source_ref == "Lecture.tex frame 1"


async def test_retry_reuses_sections_completed_before_provider_failure(tmp_path) -> None:
    checkpoints = SectionPlanCheckpointStore(
        tmp_path / "sections.json", source_revision="source-revision-1"
    )
    first_client = _LateFatalSectionPlanClient()

    with pytest.raises(ModelExecutionError, match="provider rejected"):
        await plan_sections_individually(
            model_client=first_client,
            settings=_settings(),
            source_document=_source_document(4),
            checkpoint_store=checkpoints,
        )

    retry_client = _SectionOnlyPlanClient()
    planned = await plan_sections_individually(
        model_client=retry_client,
        settings=_settings(),
        source_document=_source_document(4),
        checkpoint_store=checkpoints,
    )

    assert retry_client.source_ids == ["source-3", "source-4"]
    assert len(planned.sections) == 4


class _ControlledPlanClient:
    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self.started = 0
        self.pending: list[asyncio.Future[None]] = []
        self.started_changed = asyncio.Condition()

    async def complete_plan(self, *, settings, messages):
        source_id = _source_id(messages)
        release = asyncio.get_running_loop().create_future()
        self.pending.append(release)
        async with self.started_changed:
            self.started += 1
            self.started_changed.notify_all()
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await release
        self.active -= 1
        return _section_payload(source_id)

    async def wait_until_started(self, count: int) -> None:
        async with self.started_changed:
            await asyncio.wait_for(
                self.started_changed.wait_for(lambda: self.started >= count), timeout=1
            )

    def release(self, count: int) -> None:
        for _ in range(count):
            self.pending.pop(0).set_result(None)


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


class _ExhaustedProviderSectionPlanClient:
    def __init__(self) -> None:
        self.calls = 0

    async def complete_plan(self, *, settings, messages):
        self.calls += 1
        try:
            raise TimeoutError("provider timeout")
        except TimeoutError as cause:
            raise ModelExecutionError("The model provider timed out.") from cause


async def test_section_planner_does_not_repeat_exhausted_provider_retries() -> None:
    client = _ExhaustedProviderSectionPlanClient()

    with pytest.raises(ModelExecutionError, match="timed out"):
        await plan_sections_individually(
            model_client=client,
            settings=_settings(),
            source_document=_source_document(1),
        )

    assert client.calls == 1


async def test_section_planner_cancels_sibling_provider_calls_after_fatal_failure() -> None:
    client = _FatalSectionPlanClient()

    with pytest.raises(ModelExecutionError, match="provider rejected"):
        await plan_sections_individually(
            model_client=client,
            settings=_settings(),
            source_document=_source_document(4),
        )

    await asyncio.wait_for(client.in_flight_sibling_cancelled.wait(), timeout=1)
    assert client.started < 4
    assert "source-2" in client.cancelled_source_ids


class _FatalSectionPlanClient:
    def __init__(self) -> None:
        self.started = 0
        self.started_two = asyncio.Event()
        self.cancelled_source_ids: set[str] = set()
        self.in_flight_sibling_cancelled = asyncio.Event()

    async def complete_plan(self, *, settings, messages):
        source_id = _source_id(messages)
        try:
            self.started += 1
            if self.started == 2:
                self.started_two.set()
            await self.started_two.wait()
            if source_id == "source-1":
                try:
                    raise TimeoutError("provider rejected")
                except TimeoutError as cause:
                    raise ModelExecutionError("provider rejected") from cause
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled_source_ids.add(source_id)
            if source_id == "source-2":
                self.in_flight_sibling_cancelled.set()
            raise


class _LateFatalSectionPlanClient:
    def __init__(self) -> None:
        self.completed = 0
        self.two_completed = asyncio.Event()

    async def complete_plan(self, *, settings, messages):
        source_id = _source_id(messages)
        if source_id in {"source-1", "source-2"}:
            self.completed += 1
            if self.completed == 2:
                self.two_completed.set()
            return _section_payload(source_id)
        if source_id == "source-3":
            await self.two_completed.wait()
            try:
                raise TimeoutError("provider rejected")
            except TimeoutError as cause:
                raise ModelExecutionError("provider rejected") from cause
        await asyncio.Event().wait()


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
    async def review(self, **_kwargs) -> list:
        return []

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
