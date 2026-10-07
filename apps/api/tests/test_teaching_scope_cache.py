import json

from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.course_practice_design_planner import PracticeDesignPlanner
from lecturepilot.teaching_design_runtime import run_implementation_repair
from test_practice_design_semantic_review import _Registry
from practice_design_test_helpers import passing_review
import test_teaching_design_workspace as fixtures


async def test_identical_accepted_implementation_reuses_scope_review(tmp_path, monkeypatch):
    workspace = fixtures.workspace.__wrapped__(tmp_path)
    calls = []
    scope_inputs = []

    def respond(messages, info):
        calls.append(info)
        output = info.model_request_parameters.output_object
        if output and "coherent" in output.json_schema.get("properties", {}):
            scope_inputs.append(messages[-1].parts[-1].content)
            return ModelResponse(
                parts=[
                    TextPart(
                        json.dumps(
                            {
                                "coherent": True,
                                "reason": "The goals cover the objective.",
                                "evidence_ids": ["e0"],
                            }
                        )
                    )
                ]
            )
        if len(calls) in {2, 4}:
            return ModelResponse(parts=[ToolCallPart("validate", {})])
        return ModelResponse(parts=[ToolCallPart("final_result", {"ready": True})])

    class Critic:
        async def complete_review(self, **kwargs):
            return passing_review().model_dump(mode="json")

    planner = PracticeDesignPlanner(
        provider_registry=_Registry(), model=FunctionModel(respond), review_client=Critic()
    )
    args = dict(
        planner=planner,
        root=tmp_path / "implementation",
        authorize=lambda: None,
        source=workspace.source,
        source_revision="a" * 64,
        allowed_source_paths=workspace.paths,
        initial=workspace.proposal(),
        protected_intent=workspace.intent,
        repair_context=None,
    )
    first = await run_implementation_repair(**args)
    count = len(calls)
    second = await run_implementation_repair(**args)
    assert second == first
    assert len(calls) == count

    # A new repair context creates another implementation session, but reuses the
    # exact same intent/evidence scope verdict.
    repaired = await run_implementation_repair(
        **{**args, "repair_context": "Repair teaching details."}
    )
    assert repaired == first
    assert len(scope_inputs) == 1
    count = len(calls)

    assert list(json.loads(scope_inputs[0])) == ["evidence", "proposal"]
    assert calls[0].model_settings["openai_reasoning_effort"] == "high"
    from lecturepilot.teaching_design_runtime import scope_review_instructions

    original = scope_review_instructions()
    monkeypatch.setattr(
        "lecturepilot.teaching_design_runtime.scope_review_instructions",
        lambda: original + " Updated review guidance.",
    )
    third = await run_implementation_repair(**args)
    assert third == first
    assert len(calls) == count + 1
