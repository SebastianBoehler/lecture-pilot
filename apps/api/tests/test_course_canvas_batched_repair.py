import asyncio

import pytest

from lecturepilot.course_canvas_auto_repair import repair_until_quality_valid
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_quality import CanvasQualityIssue
from test_course_canvas_quality import _source_document
from test_course_canvas_targeted_repair import _invalid_candidate


async def test_quality_issues_in_one_section_are_repaired_in_one_batch() -> None:
    source, candidate = _documents()
    issues = [
        CanvasQualityIssue(
            section_id="learning-optimization",
            block_id=f"optimization-issue-{index}",
            reason=f"quality issue {index}",
        )
        for index in range(1, 6)
    ]
    planner = _BatchPlanner(reviews=[[]])

    repaired = await repair_until_quality_valid(
        planner,
        source=source,
        candidate=candidate,
        section_id=issues[0].section_id,
        block_id=issues[0].block_id,
        failure_context="Canvas quality review failed.",
        output_language="en",
        quality_issues=issues,
    )

    assert repaired == candidate
    assert planner.review_calls == 1
    assert len(planner.repair_calls) == 1
    section_id, block_id, failure = planner.repair_calls[0]
    assert section_id == "learning-optimization"
    assert block_id is None
    assert failure.startswith("Canvas quality review failed:")
    assert all(f"quality issue {index}" in failure for index in range(1, 6))


async def test_batched_quality_repair_allows_one_bounded_follow_up_pass() -> None:
    source, candidate = _documents()
    issue = CanvasQualityIssue(
        section_id="learning-optimization",
        block_id="optimization-intro",
        reason="The explanation remains unsupported.",
    )
    planner = _BatchPlanner(reviews=[[issue], []])

    repaired = await repair_until_quality_valid(
        planner,
        source=source,
        candidate=candidate,
        section_id=issue.section_id,
        block_id=issue.block_id,
        failure_context="Canvas quality review failed.",
        output_language="en",
        quality_issues=[issue],
    )

    assert repaired == candidate
    assert planner.review_calls == 2
    assert len(planner.repair_calls) == 2


async def test_batched_quality_repair_stops_after_two_passes() -> None:
    source, candidate = _documents()
    issue = CanvasQualityIssue(
        section_id="learning-optimization",
        block_id="optimization-intro",
        reason="The explanation remains unsupported.",
    )
    planner = _BatchPlanner(reviews=[[issue], [issue]])

    with pytest.raises(CanvasGenerationRepairableError, match="remains unsupported") as caught:
        await repair_until_quality_valid(
            planner,
            source=source,
            candidate=candidate,
            section_id=issue.section_id,
            block_id=issue.block_id,
            failure_context="Canvas quality review failed.",
            output_language="en",
            quality_issues=[issue],
        )

    assert caught.value.candidate == candidate
    assert planner.review_calls == 2
    assert len(planner.repair_calls) == 2


async def test_quality_issues_in_separate_sections_are_repaired_concurrently() -> None:
    source, candidate = _documents()
    issues = [
        CanvasQualityIssue(
            section_id=section.id,
            block_id=section.blocks[0].id,
            reason=f"repair {section.id}",
        )
        for section in candidate.sections
    ]
    planner = _ConcurrentBatchPlanner(reviews=[[]])

    await repair_until_quality_valid(
        planner,
        source=source,
        candidate=candidate,
        section_id=issues[0].section_id,
        block_id=issues[0].block_id,
        failure_context="Canvas quality review failed.",
        output_language="en",
        quality_issues=issues,
    )

    assert planner.max_active_repairs == 2
    assert planner.review_calls == 1


async def test_persisted_quality_failure_rediscovers_all_section_coordinates_before_repair() -> None:
    source, candidate = _documents()
    issues = [
        CanvasQualityIssue(
            section_id=section.id,
            block_id=section.blocks[0].id,
            reason=f"repair {section.id}",
        )
        for section in candidate.sections
    ]
    planner = _BatchPlanner(reviews=[issues, []])

    await repair_until_quality_valid(
        planner,
        source=source,
        candidate=candidate,
        section_id=issues[0].section_id,
        block_id=None,
        failure_context=(
            "Canvas quality review failed: fix every reported issue together:\n"
            "- persisted cross-section issues"
        ),
        output_language="en",
    )

    assert planner.review_calls == 2
    assert {call[0] for call in planner.repair_calls} == {
        "learning-optimization",
        "learning-summary",
    }
    assert len(planner.repair_calls) == 2


class _BatchPlanner:
    def __init__(self, *, reviews: list[list[CanvasQualityIssue]]) -> None:
        self.reviews = reviews
        self.review_calls = 0
        self.repair_calls: list[tuple[str, str | None, str]] = []

    async def repair_section(
        self,
        source_document,
        candidate_document,
        *,
        section_id,
        block_id,
        failure_context,
        output_language,
    ):
        self.repair_calls.append((section_id, block_id, failure_context))
        return candidate_document

    async def review_quality(self, source_document, candidate_document):
        self.review_calls += 1
        return self.reviews.pop(0)


class _ConcurrentBatchPlanner(_BatchPlanner):
    def __init__(self, *, reviews: list[list[CanvasQualityIssue]]) -> None:
        super().__init__(reviews=reviews)
        self.active_repairs = 0
        self.max_active_repairs = 0

    async def repair_section(self, *args, **kwargs):
        self.active_repairs += 1
        self.max_active_repairs = max(self.max_active_repairs, self.active_repairs)
        try:
            await asyncio.sleep(0.01)
            return await super().repair_section(*args, **kwargs)
        finally:
            self.active_repairs -= 1


def _documents():
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
    return source, candidate
