import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_planner import CourseCanvasPlanner
from lecturepilot.course_canvas_quality import (
    CanvasQualityReviewer,
)
from lecturepilot.models import ProviderSettings
from lecturepilot.providers import ProviderConfigurationError, ProviderRegistry
from test_course_canvas_targeted_repair import _invalid_candidate


async def test_quality_reviewer_rejects_a_wrong_selected_quiz_answer() -> None:
    document = _source_document()
    reviewer = CanvasQualityReviewer(
        model_client=_QualityClient(
            [
                {
                    "section_id": "topic",
                    "block_id": "quiz",
                    "reason": "The selected option contradicts the supplied lecture evidence.",
                }
            ]
        )
    )

    with pytest.raises(CanvasGenerationRepairableError, match="selected option contradicts"):
        await reviewer.validate(
            settings=_settings(),
            source_document=document,
            candidate_document=document,
        )


async def test_quality_reviewer_rejects_unknown_issue_coordinates() -> None:
    document = _source_document()
    reviewer = CanvasQualityReviewer(
        model_client=_QualityClient(
            [
                {
                    "section_id": "missing-section",
                    "block_id": None,
                    "reason": "Unsupported claim.",
                }
            ]
        )
    )

    with pytest.raises(ProviderConfigurationError, match="unknown section"):
        await reviewer.validate(
            settings=_settings(),
            source_document=document,
            candidate_document=document,
        )


async def test_course_planner_regenerates_once_with_quality_feedback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    model = _PlanClient()
    quality = _SequencedQualityReviewer()
    planner = CourseCanvasPlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=model,
        quality_reviewer=quality,
    )

    document = await planner.plan_canvas(_source_document())

    assert document.sections[0].id == "learning-1-topic"
    assert model.calls == 2
    assert quality.calls == 2
    assert "answer key is not supported" in model.repair_prompts[0]


async def test_quality_failure_forces_a_source_grounded_patch_of_valid_structure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    model = _RepairClient()
    source = _source_document()
    candidate = _invalid_candidate(source)
    section = candidate.sections[0]
    valid_math = section.blocks[1].model_copy(update={"text": r"w^\top x"})
    candidate = candidate.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={"blocks": [section.blocks[0], valid_math, *section.blocks[2:]]}
                ),
                candidate.sections[1],
            ]
        }
    )
    planner = CourseCanvasPlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=model,
        quality_reviewer=_AlwaysPassQualityReviewer(),
    )

    repaired = await planner.repair_section(
        source,
        candidate,
        section_id="learning-optimization",
        block_id="optimization-intro",
        failure_context=(
            "Canvas quality review failed: the teaching claim is not supported by the source."
        ),
    )

    assert model.calls == 1
    assert repaired.sections[0].blocks[0].text.startswith("The corrected explanation")


class _QualityClient:
    def __init__(self, issues: list[dict]) -> None:
        self.issues = issues

    async def complete_review(self, *, settings, source_document, candidate_document):
        return {"issues": self.issues}


class _SequencedQualityReviewer:
    def __init__(self) -> None:
        self.calls = 0

    async def validate(self, **_kwargs) -> None:
        self.calls += 1
        if self.calls == 1:
            raise CanvasGenerationRepairableError(
                "Canvas quality review failed: answer key is not supported.",
                section_id="topic",
                block_id="quiz",
            )


class _PlanClient:
    def __init__(self) -> None:
        self.calls = 0
        self.repair_prompts: list[str] = []

    async def complete_plan(self, *, settings, messages):
        self.calls += 1
        if len(messages) > 2:
            self.repair_prompts.append(messages[-1]["content"])
        return {
            "title": "Lecture",
            "sections": [
                {
                    "id": "topic",
                    "title": "Topic",
                    "source_ref": "lecture.pdf page 1",
                    "blocks": [
                        *[
                            {
                                "type": "paragraph",
                                "text": (
                                    "The lecture states the source-backed mechanism, explains "
                                    "when it applies, and names a concrete failure mode. "
                                )
                                * 3,
                            }
                            for _ in range(4)
                        ],
                        {
                            "type": "quiz",
                            "text": "Which statement matches the lecture?",
                            "items": ["Unsupported claim", "Source-backed statement"],
                            "answer_index": 1,
                        },
                    ],
                }
            ],
        }


class _RepairClient:
    def __init__(self) -> None:
        self.calls = 0

    async def complete_plan(self, *, settings, messages, temperature=0.2):
        self.calls += 1
        return {
            "sections": [
                {
                    "id": "replacement",
                    "title": "Corrected explanation",
                    "source_ref": "lecture.pdf page 1",
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text": (
                                "The corrected explanation follows the supplied source evidence "
                                "and removes the unsupported teaching claim."
                            ),
                        }
                    ],
                }
            ]
        }


class _AlwaysPassQualityReviewer:
    async def validate(self, **_kwargs) -> None:
        return None


def _source_document() -> CanvasDocument:
    return CanvasDocument(
        id="course-lecture",
        course_id="course",
        lecture_id="lecture",
        title="Lecture",
        source_kind="generated",
        source_ref="lecture.pdf",
        workspace_path="canvas/index.md",
        sections=[
            CanvasSection(
                id="topic",
                title="Topic",
                source_ref="lecture.pdf page 1",
                blocks=[
                    CanvasBlock(
                        id="source",
                        type="paragraph",
                        text=(
                            "The source-backed statement is correct. It describes the mechanism, "
                            "when it applies, and a concrete failure mode."
                        ),
                    ),
                    CanvasBlock(
                        id="quiz",
                        type="quiz",
                        text="Which statement matches the lecture?",
                        items=["Unsupported claim", "Source-backed statement"],
                        answer_index=1,
                    ),
                ],
            )
        ],
    )


def _settings() -> ProviderSettings:
    return ProviderSettings(
        provider="test",
        model="test/model",
        api_key_env="TEST_API_KEY",
        capabilities=set(),
    )
