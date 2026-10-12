import pytest
import json
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.authoring_job import run_authoring_job
from lecturepilot.authoring_models import AuthoringDesignConflict
from lecturepilot.authoring_checkpoint_review import CheckpointReviewer
from lecturepilot.course_canvas_quality import CanvasQualityReviewer
from authoring_test_helpers import markdown
from test_authoring_job import authoring_job


async def test_agent_cannot_rewrite_approved_task_to_satisfy_critic(tmp_path):
    job = authoring_job(tmp_path)
    job.candidate = job.source.model_copy(deep=True)
    job.candidate.sections[0].source_section_id = "topic"

    class Critic:
        async def complete_review(self, **kwargs):
            return {
                "issues": [
                    {
                        "section_id": "topic",
                        "block_id": "practice-" + job.design.targets[0].id,
                        "reason": "The approved task requires unsupported evidence.",
                    }
                ]
            }

    job.reviewer = CanvasQualityReviewer(Critic())
    job.checkpoint_reviewer = CheckpointReviewer(
        model=FunctionModel(
            lambda messages, info: ModelResponse(
                parts=[
                    TextPart(
                        json.dumps(
                            {
                                "decision": "design_conflict",
                                "reason": "The approved task requires unsupported evidence.",
                                "evidence_ids": ["e0"],
                            }
                        )
                    )
                ]
            )
        )
    )
    calls = 0

    def respond(messages, info):
        nonlocal calls
        calls += 1
        raise AssertionError("A confirmed design conflict needs no section rewrite.")

    with pytest.raises(AuthoringDesignConflict, match="approved practice design"):
        await run_authoring_job(job, model=FunctionModel(respond))
    assert calls == 0


async def test_false_checkpoint_objection_does_not_veto_completion(tmp_path):
    job = authoring_job(tmp_path)
    job.candidate = job.source.model_copy(deep=True)
    job.candidate.sections[0].source_section_id = "topic"

    class Critic:
        async def complete_review(self, **kwargs):
            return {
                "issues": [
                    {
                        "section_id": "topic",
                        "block_id": "practice-" + job.design.targets[0].id,
                        "reason": "Choose one must have only one defensible answer.",
                    }
                ]
            }

    job.reviewer = CanvasQualityReviewer(Critic())
    job.checkpoint_reviewer = CheckpointReviewer(
        model=FunctionModel(
            lambda messages, info: ModelResponse(
                parts=[
                    TextPart(
                        json.dumps(
                            {
                                "decision": "dismiss",
                                "reason": "The task permits any justified conclusion; the rubric accepts it.",
                                "evidence_ids": ["e0"],
                            }
                        )
                    )
                ]
            )
        )
    )
    result = await run_authoring_job(
        job, model=FunctionModel(lambda messages, info: pytest.fail("no rewrite needed"))
    )
    assert result.document.sections[0].blocks[0].text == job.design.targets[0].baseline_task
    assert not result.document.warnings


async def test_missing_teaching_is_repaired_without_rewriting_approved_task(tmp_path):
    job = authoring_job(tmp_path)
    job.candidate = job.source.model_copy(deep=True)
    job.candidate.sections[0].source_section_id = "topic"

    class Critic:
        async def complete_review(self, *, candidate_document, **kwargs):
            taught = any(
                "Worked example" in b.text for s in candidate_document.sections for b in s.blocks
            )
            return {
                "issues": []
                if taught
                else [
                    {
                        "section_id": "topic",
                        "block_id": "practice-" + job.design.targets[0].id,
                        "reason": "The source-supported method needs a worked example in the teaching.",
                    }
                ]
            }

    job.reviewer = CanvasQualityReviewer(Critic())
    job.checkpoint_reviewer = CheckpointReviewer(
        model=FunctionModel(
            lambda messages, info: ModelResponse(
                parts=[
                    TextPart(
                        json.dumps(
                            {
                                "decision": "repair_teaching",
                                "reason": "Add a worked example to the teaching, keeping the approved task.",
                                "evidence_ids": ["e0"],
                            }
                        )
                    )
                ]
            )
        )
    )
    calls = 0

    def respond(messages, info):
        nonlocal calls
        calls += 1
        assert "Add a worked example" in str(messages)
        draft = str(messages[0].parts[-1].content).split("Current draft:\n")[1].split("\nNotes")[0]
        return markdown(
            draft.replace(
                "The variable x denotes evidence.",
                "The variable x denotes evidence. Worked example: use x to justify the claim.",
            )
        )

    result = await run_authoring_job(job, model=FunctionModel(respond))
    assert calls == 1
    assert result.document.sections[0].blocks[0].text == job.design.targets[0].baseline_task
    assert result.metrics.repair_edits == 1
    assert not result.document.warnings
