import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_planner import CourseCanvasPlanner
from lecturepilot.course_canvas_quality import CanvasQualityIssue
from lecturepilot.providers import ProviderRegistry


async def test_exhausted_quality_repair_budget_is_not_started_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    candidate = _candidate()

    async def plan_sections(**_kwargs) -> CanvasDocument:
        return candidate

    monkeypatch.setattr(
        "lecturepilot.course_canvas_planner.plan_sections_individually",
        plan_sections,
    )
    reviewer = _AlwaysIssueReviewer()
    planner = _NoopRepairPlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        quality_reviewer=reviewer,
    )

    with pytest.raises(CanvasGenerationRepairableError, match="unsupported"):
        await planner.plan_canvas(candidate)

    assert reviewer.calls == 3
    assert planner.repair_calls == 2


class _AlwaysIssueReviewer:
    def __init__(self) -> None:
        self.calls = 0

    async def review(self, **_kwargs) -> list[CanvasQualityIssue]:
        self.calls += 1
        return [
            CanvasQualityIssue(
                section_id="topic",
                block_id="claim",
                reason="The claim remains unsupported.",
            )
        ]


class _NoopRepairPlanner(CourseCanvasPlanner):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.repair_calls = 0

    async def repair_section(self, _source, candidate, **_kwargs) -> CanvasDocument:
        self.repair_calls += 1
        return candidate


def _candidate() -> CanvasDocument:
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
                    CanvasBlock(id="claim", type="paragraph", text="Unsupported claim."),
                    CanvasBlock(
                        id="check",
                        type="checkpoint",
                        text="Explain the supported mechanism in one sentence.",
                    ),
                ],
            )
        ],
    )
