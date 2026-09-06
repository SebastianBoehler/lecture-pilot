from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
import pytest
from lecturepilot.authoring_state import AuthoringStateError
from lecturepilot.authoring_provider import MeteredAuthoringModel

from lecturepilot.authoring_job import AuthoringJob, run_authoring_job
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_quality import CanvasQualityReviewer
from lecturepilot.models import ProviderSettings
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


async def test_authoring_agent_repairs_invalid_math_and_preserves_approved_task(tmp_path):
    job = authoring_job(tmp_path)
    steps = iter(
        [
            (
                "write",
                {
                    "path": "/draft/topic.md",
                    "text": (
                        '<!-- block id="explanation" type="paragraph" -->\n'
                        "A justified conclusion connects relevant evidence to the claim.\n\n"
                        '<!-- block id="formula" type="math" -->\n```math\n\\custom{x}\n```\n'
                    ),
                },
            ),
            ("validate", {}),
            ("edit", {"path": "/draft/topic.md", "old": "\\custom{x}", "new": "x"}),
            ("validate", {}),
            ("final_result", {"ready": True}),
        ]
    )

    def respond(messages, info):
        name, args = next(steps)
        return ModelResponse(parts=[ToolCallPart(name, args)])

    model = MeteredAuthoringModel(FunctionModel(respond), job.settings, None, job.authorize)
    result = await run_authoring_job(job, model=model)

    assert result.document.sections[0].blocks[-1].text == "x"
    assert result.document.sections[0].blocks[0].text == job.design.targets[0].baseline_task
    assert result.metrics.validation_failures == 1
    assert result.metrics.repair_edits == 1


async def test_job_resumes_saved_tools_and_draft_after_worker_failure(tmp_path):
    job = authoring_job(tmp_path)
    calls = 0

    def interrupted(messages, info):
        nonlocal calls
        calls += 1
        if calls == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "write",
                        {
                            "path": "/draft/topic.md",
                            "text": '<!-- block id="explanation" type="paragraph" -->\nA justified conclusion connects evidence to the claim.',
                        },
                    )
                ]
            )
        raise RuntimeError("worker disconnected")

    with pytest.raises(RuntimeError, match="worker disconnected"):
        await run_authoring_job(job, model=FunctionModel(interrupted))

    def resume(messages, info):
        assert any(
            getattr(part, "tool_name", "") == "write"
            for message in messages
            for part in message.parts
        )
        return ModelResponse(parts=[ToolCallPart("final_result", {"ready": True})])

    result = await run_authoring_job(authoring_job(tmp_path), model=FunctionModel(resume))
    assert result.document.sections[0].blocks[-1].text.endswith("evidence to the claim.")
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


@pytest.mark.parametrize(
    "path", ["/etc/passwd", "/user/memories/global.md", "/evidence/../secret", "/draft/.env"]
)
async def test_agent_receives_denial_for_unauthorized_reads(tmp_path, path):
    calls = 0

    def respond(messages, info):
        nonlocal calls
        calls += 1
        if calls == 1:
            return ModelResponse(parts=[ToolCallPart("read", {"path": path})])
        assert messages[-1].parts[0].part_kind == "retry-prompt"
        raise RuntimeError("denial observed")

    with pytest.raises(RuntimeError, match="denial observed"):
        await run_authoring_job(authoring_job(tmp_path), model=FunctionModel(respond))
