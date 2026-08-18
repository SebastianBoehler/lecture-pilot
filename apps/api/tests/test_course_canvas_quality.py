import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_planner import CourseCanvasPlanner
from lecturepilot.course_canvas_quality import (
    CanvasQualityReviewer,
    _quality_messages,
)
from lecturepilot.models import ProviderSettings
from lecturepilot.providers import ProviderRegistry
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


def test_quality_review_treats_checkpoints_as_open_answer_tasks() -> None:
    document = _source_document()

    prompt = _quality_messages(document, document)[0]["content"]

    assert "A checkpoint is an open-answer task" in prompt
    assert "does not need answer options" in prompt
    assert "copy its id verbatim" in prompt
    assert "use null" in prompt


async def test_quality_reviewer_preserves_detailed_issue_reasoning() -> None:
    document = _source_document()
    detailed_reason = "Unsupported derivation detail. " * 30
    reviewer = CanvasQualityReviewer(
        model_client=_QualityClient(
            [
                {
                    "section_id": "topic",
                    "block_id": "source",
                    "reason": detailed_reason,
                }
            ]
        )
    )

    with pytest.raises(CanvasGenerationRepairableError) as caught:
        await reviewer.validate(
            settings=_settings(),
            source_document=document,
            candidate_document=document,
        )

    assert detailed_reason.strip() in str(caught.value)


async def test_quality_reviewer_reviews_each_section_without_cross_section_truncation() -> None:
    source = _source_document()
    first = source.sections[0].model_copy(
        update={
            "blocks": [
                CanvasBlock(
                    id="large-first-claim",
                    type="paragraph",
                    text="First source-grounded claim. " * 350,
                )
            ]
        }
    )
    second = source.sections[0].model_copy(
        update={
            "id": "second-topic",
            "title": "Second topic",
            "source_ref": "lecture.pdf page 2",
            "blocks": [
                CanvasBlock(
                    id="complete-formula",
                    type="math",
                    text=(
                        r"P(x\mid C=1)P(C=1) > P(x\mid C=0)P(C=0). "
                        + "Second source-grounded derivation. " * 300
                    ),
                )
            ],
        }
    )
    source = source.model_copy(update={"sections": [first, second]})
    client = _SectionIsolatedQualityClient()
    reviewer = CanvasQualityReviewer(model_client=client)

    assert (
        await reviewer.review(
            settings=_settings(),
            source_document=source,
            candidate_document=source,
        )
        == []
    )

    assert sorted(client.reviewed_sections) == [["second-topic"], ["topic"]]


async def test_quality_reviewer_targets_the_section_when_multiple_blocks_fail() -> None:
    document = _source_document()
    reviewer = CanvasQualityReviewer(
        model_client=_QualityClient(
            [
                {
                    "section_id": "topic",
                    "block_id": "quiz",
                    "reason": "The selected answer is unsupported.",
                },
                {
                    "section_id": "topic",
                    "block_id": "source",
                    "reason": "The task depends on omitted code.",
                },
            ]
        )
    )

    with pytest.raises(CanvasGenerationRepairableError) as caught:
        await reviewer.validate(
            settings=_settings(),
            source_document=document,
            candidate_document=document,
        )

    assert caught.value.section_id == "topic"
    assert caught.value.block_id is None


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


class _SectionIsolatedQualityClient:
    def __init__(self) -> None:
        self.reviewed_sections: list[list[str]] = []

    async def complete_review(self, *, settings, source_document, candidate_document):
        section_ids = [section.id for section in candidate_document.sections]
        self.reviewed_sections.append(section_ids)
        assert len(candidate_document.sections) == 1
        return {"issues": []}


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
    async def review(self, **_kwargs) -> list:
        return []

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
