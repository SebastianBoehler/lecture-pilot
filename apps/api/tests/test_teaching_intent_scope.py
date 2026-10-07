import json

import pytest
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.authoring_models import AuthoringDesignConflict
from lecturepilot.course_practice_design_planner import PracticeDesignPlanner
from lecturepilot.teaching_design_runtime import run_implementation_repair
from test_practice_design_semantic_review import _Registry
import test_teaching_design_workspace as workspace_fixtures


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_evidence_first", [False, True])
async def test_approved_scope_conflict_stops_before_teaching_edits(
    tmp_path, invalid_evidence_first
):
    workspace = workspace_fixtures.workspace.__wrapped__(tmp_path)
    calls = 0

    def respond(messages, info):
        nonlocal calls
        calls += 1
        assert info.model_request_parameters.output_mode == "native"
        if calls == 1:
            instructions = info.instructions
            assert "derive consequences from its formulas or definitions" in instructions
            assert "Do not introduce unrelated topics" in instructions
            assert set(json.loads(messages[-1].parts[0].content)["proposal"]) == {
                "objective",
                "goals",
            }
        return ModelResponse(
            parts=[
                TextPart(
                    json.dumps(
                        {
                            "coherent": False,
                            "reason": "The objective promises a capability absent from the approved goal set.",
                            "evidence_ids": [
                                "unknown" if invalid_evidence_first and calls == 1 else "e0"
                            ],
                        }
                    )
                )
            ]
        )

    planner = PracticeDesignPlanner(provider_registry=_Registry(), model=FunctionModel(respond))
    root = tmp_path / "implementation"
    intent = workspace.intent.model_copy(deep=True)
    with pytest.raises(AuthoringDesignConflict, match="Review and edit the learning plan"):
        await run_implementation_repair(
            planner=planner,
            root=root,
            authorize=lambda: None,
            source=workspace.source,
            source_revision="a" * 64,
            allowed_source_paths=workspace.paths,
            initial=workspace.proposal(),
            protected_intent=workspace.intent,
            repair_context=None,
        )
    assert calls == (2 if invalid_evidence_first else 1)
    assert not root.exists()
    assert workspace.intent == intent
