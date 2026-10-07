from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_quality import (
    CanvasQualityReviewer,
    _quality_messages,
)
from lecturepilot.models import ProviderSettings


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

    issues = await reviewer.review(
        settings=_settings(), source_document=document, candidate_document=document
    )
    assert "selected option contradicts" in issues[0].reason


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

    issues = await reviewer.review(
        settings=_settings(), source_document=document, candidate_document=document
    )
    assert issues[0].reason == detailed_reason


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

    issues = await reviewer.review(
        settings=_settings(), source_document=document, candidate_document=document
    )
    assert [issue.block_id for issue in issues] == ["quiz", "source"]


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

    async def complete_plan(self, *, settings, messages, temperature=0.2, response_format=None):
        self.calls += 1
        return {
            "edits": [
                {
                    "operation": "replace_block",
                    "section_id": "learning-optimization",
                    "block_id": "optimization-intro",
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
