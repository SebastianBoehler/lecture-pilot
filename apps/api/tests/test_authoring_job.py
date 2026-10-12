from pydantic_ai.models.function import FunctionModel
import pytest
from lecturepilot.authoring_state import AuthoringStateError
from lecturepilot.authoring_provider import MeteredAuthoringModel

from lecturepilot.authoring_job import AuthoringJob, run_authoring_job
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_quality import CanvasQualityReviewer
from lecturepilot.models import ProviderSettings
from authoring_test_helpers import drafted_path, is_repair, markdown
from practice_design_test_helpers import practice_design_for_canvas


def source_document():
    return CanvasDocument(
        id="lecture-01",
        course_id="course-a",
        lecture_id="lecture-01",
        title="Evidence",
        source_kind="markdown",
        source_ref="lecture.md",
        workspace_path="source/lecture.md",
        sections=[
            CanvasSection(
                id="topic",
                title="Evidence",
                source_ref="lecture.md",
                blocks=[
                    CanvasBlock(
                        id="evidence",
                        type="paragraph",
                        text="A justified conclusion connects relevant evidence to the claim. The variable x denotes evidence.",
                    )
                ],
            )
        ],
    )


class ReviewClient:
    async def complete_review(self, **kwargs):
        return {"issues": []}


def authoring_job(tmp_path):
    source = source_document()
    return AuthoringJob(
        root=tmp_path / "job",
        source=source,
        design=practice_design_for_canvas(source),
        source_revision="a" * 64,
        settings=ProviderSettings(
            provider="openai", model="openai/test", api_key_env="OPENAI_API_KEY", capabilities=set()
        ),
        reviewer=CanvasQualityReviewer(ReviewClient()),
    )


VALID = (
    '<!-- block id="explanation" type="paragraph" -->\n'
    "A justified conclusion connects relevant evidence to the claim.\n"
)


async def test_section_author_repairs_invalid_math_and_preserves_approved_task(tmp_path):
    job = authoring_job(tmp_path)
    outputs = iter(
        [
            VALID + '\n<!-- block id="formula" type="math" -->\n```math\n\\custom{x}\n```\n',
            VALID + '\n<!-- block id="formula" type="math" -->\n```math\nx\n```\n',
        ]
    )

    def respond(messages, info):
        assert drafted_path(messages) == "/draft/topic.md"
        return markdown(next(outputs))

    model = MeteredAuthoringModel(FunctionModel(respond), job.settings, None, job.authorize)
    result = await run_authoring_job(job, model=model)

    assert result.document.sections[0].blocks[-1].text == "x"
    assert result.document.sections[0].blocks[0].text == job.design.targets[0].baseline_task
    assert result.metrics.validation_failures == 1
    assert not result.document.warnings


async def test_saved_sections_are_not_rewritten_when_a_job_resumes(tmp_path):
    job = authoring_job(tmp_path)
    calls = 0

    class FailingReview:
        async def complete_review(self, **kwargs):
            raise RuntimeError("critic disconnected")

    def respond(messages, info):
        nonlocal calls
        calls += 1
        return markdown(VALID)

    job.reviewer = CanvasQualityReviewer(FailingReview())
    with pytest.raises(RuntimeError, match="critic disconnected"):
        await run_authoring_job(job, model=FunctionModel(respond))
    assert calls == 1

    result = await run_authoring_job(authoring_job(tmp_path), model=FunctionModel(respond))
    assert calls == 1
    assert result.document.sections[-1].blocks[-1].text.endswith("evidence to the claim.")
    assert result.metrics.resumes == 1


async def test_resuming_changed_source_is_rejected_before_model_call(tmp_path):
    job = authoring_job(tmp_path)

    def fail(messages, info):
        raise RuntimeError("connection lost")

    with pytest.raises(RuntimeError):
        await run_authoring_job(job, model=FunctionModel(fail))
    job.source_revision = "b" * 64
    with pytest.raises(AuthoringStateError, match="changed"):
        await run_authoring_job(job, model=FunctionModel(fail))


async def test_open_critic_notes_get_one_repair_then_become_draft_warnings(tmp_path):
    job = authoring_job(tmp_path)
    repairs = 0

    class Critic:
        async def complete_review(self, *, candidate_document, **kwargs):
            section = candidate_document.sections[0]
            return {"issues": [{"section_id": section.id, "reason": "Explain the claim link."}]}

    def respond(messages, info):
        nonlocal repairs
        repairs += is_repair(messages)
        if is_repair(messages):
            assert "Explain the claim link." in str(messages[0].parts[-1].content)
        return markdown(VALID)

    job.reviewer = CanvasQualityReviewer(Critic())
    result = await run_authoring_job(job, model=FunctionModel(respond))
    assert repairs == 1
    assert any("open note" in warning for warning in result.document.warnings)
