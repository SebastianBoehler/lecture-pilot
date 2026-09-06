from reviewed_task_bank_helpers import with_bank
import json
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelResponse, TextPart

import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.models import ProviderCapability, ProviderSettings
from practice_design_test_helpers import passing_review, proposal, target
from lecturepilot.practice_evidence_catalogue import evidence_catalogue, compact_evidence_anchors


SOURCE_REVISION = "a" * 64


def _source() -> CanvasDocument:
    return CanvasDocument(
        id="c-l",
        course_id="c",
        lecture_id="l",
        title="Bayes rule",
        source_kind="markdown",
        source_ref="lecture.md",
        workspace_path="source.json",
        sections=[
            CanvasSection(
                id="bayes",
                title="Bayes rule",
                source_ref="lecture.md",
                blocks=[CanvasBlock(id="evidence", type="paragraph", text="Posterior evidence.")],
            )
        ],
    )


@pytest.mark.asyncio
async def test_planner_uses_native_schema_and_exact_authoritative_source_paths() -> None:
    from lecturepilot.course_practice_design_planner import PracticeDesignPlanner

    calls: list[dict] = []

    def fake_completion(messages, info):
        calls.append({"messages": messages, "instructions": info.instructions})
        catalogue = evidence_catalogue(_source(), ("lecture.md",))
        payload = (
            proposal()
            .model_copy(
                update={
                    "targets": (
                        with_bank(
                            target(
                                source_refs=("lecture.md",), source_excerpt="Posterior evidence."
                            )
                        ),
                    )
                }
            )
            .model_dump(mode="json")
        )
        wire = compact_evidence_anchors(payload, catalogue)
        wire["targets"][0].pop("source_refs")
        return ModelResponse(parts=[TextPart(json.dumps(wire))])

    class ReviewClient:
        async def complete_review(self, **kwargs):
            calls.append(kwargs)
            return passing_review().model_dump(mode="json")

    settings = ProviderSettings(
        provider="openai",
        model="openai/gpt-5.6-luna",
        api_key_env="OPENAI_API_KEY",
        capabilities={ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON},
    )

    class Registry:
        def require_ready(self, _required):
            return settings

    planner = PracticeDesignPlanner(
        provider_registry=Registry(),
        model=FunctionModel(fake_completion),
        review_client=ReviewClient(),
    )

    reviewed = await planner.propose(
        source=_source(), source_revision=SOURCE_REVISION, allowed_source_paths=("lecture.md",)
    )

    assert reviewed.proposal.targets[0].source_refs == ("lecture.md",)
    assert len(reviewed.review.checks) == 8
    assert (
        reviewed.proposal.planning_context.learner_level
        == "Undergraduate learners in this lecture."
    )
    request = calls[0]
    instruction = request["instructions"]
    assert "minimum set of distinct capabilities supported by the source" in instruction
    assert "3 to 6 targets" not in instruction
    assert "Diagnostic attempt" in instruction
    assert "Independent exit" in instruction
    assert "Delayed transfer" in instruction
    assert "Atomic evidence criteria" in instruction
    assert "prompt asks the learner to inspect or plan" in instruction
    assert "worked_step gives one justified step" in instruction
    assert "not a claim that this interval is scientifically optimal" in instruction
    assert "solve it from its stated givens" in instruction
    assert "Contradictory givens make a task unassessable" in instruction
    assert "lecture.md" in str(request["messages"])
    assert "unrouted.md" not in str(request["messages"])
    review_request = calls[1]
    assert "SOURCE EVIDENCE" in review_request["messages"][1]["content"]
    assert "solve it from its stated givens" in review_request["messages"][0]["content"]


def test_response_schema_describes_the_assessment_and_scaffold_contract() -> None:
    from lecturepilot.course_practice_design_prompt import practice_design_response_format

    schema = practice_design_response_format(evidence_catalogue(_source(), ("lecture.md",)))[
        "json_schema"
    ]["schema"]
    target_schema = schema["$defs"]["PracticeTarget"]["properties"]
    criterion_schema = schema["$defs"]["PracticeEvidenceCriterion"]["properties"]
    misconception_schema = schema["$defs"]["PracticeMisconception"]["properties"]
    hint_schema = schema["$defs"]["PracticeHint"]["properties"]

    assert "diagnostic attempt" in target_schema["baseline_task"]["description"].lower()
    assert "unaided" in target_schema["independent_exit_task"]["description"].lower()
    assert "changed-form" in target_schema["delayed_transfer_task"]["description"].lower()
    assert "atomic" in criterion_schema["description"]["description"].lower()
    assert "boundary" in misconception_schema["description"]["description"].lower()
    hint_description = hint_schema["level"]["description"]
    for level in ("prompt", "cue", "faded_example", "worked_step"):
        assert level in hint_description
