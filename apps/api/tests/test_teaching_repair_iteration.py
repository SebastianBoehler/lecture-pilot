"""A valid teaching repair must not be limited to four whole-design outputs."""

import json
import pytest

from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from lecturepilot.course_practice_design_planner import PracticeDesignPlanner
from lecturepilot.course_learning_intent import LearningGoal, LearningIntent, goal_for, digest
from lecturepilot.teaching_design_runtime import run_implementation_repair
from lecturepilot.practice_evidence_catalogue import compact_evidence_anchors, evidence_catalogue
from practice_design_test_helpers import proposal, target
from reviewed_task_bank_helpers import with_bank
from test_practice_design_semantic_review import _Registry, _source, _review_payload


@pytest.mark.parametrize("disconnect", [False, True, "budget"])
async def test_repair_can_resolve_more_than_three_review_findings(
    tmp_path, disconnect, monkeypatch
):
    source = _source()
    design = proposal().model_copy(
        update={
            "targets": (
                with_bank(
                    target(
                        source_refs=("lecture-01.md",),
                        source_excerpt=source.sections[0].blocks[0].text,
                    )
                ),
            )
        }
    )
    wire = compact_evidence_anchors(
        design.model_dump(mode="json"), evidence_catalogue(source, ("lecture-01.md",))
    )
    wire["targets"][0].pop("source_refs")
    reviews = 0

    payload = dict(
        source_revision="a" * 64,
        objective=design.objective,
        planning_context=design.planning_context.model_dump(mode="json"),
        goals=[goal_for(t).model_dump(mode="json") for t in design.targets],
        fixed_targets=[],
    )
    intent = LearningIntent.model_validate({**payload, "revision": digest(payload)})
    teaching = wire["targets"][0]
    for key in LearningGoal.model_fields:
        if key != "id":
            teaching.pop(key)
    calls = 0
    interrupted = False

    def respond(messages, info):
        nonlocal calls, interrupted
        if disconnect is True and calls == 1 and not interrupted:
            interrupted = True
            raise RuntimeError("Provider connection interrupted after saved write")
        calls += 1
        if reviews == 5:
            return ModelResponse(parts=[ToolCallPart("final_result", {"ready": True})])
        if calls % 2 == 0:
            return ModelResponse(parts=[ToolCallPart("validate", {})])
        teaching["evidence_criteria"][0]["description"] = (
            f"Explain the evidence, revision {reviews}."
        )
        return ModelResponse(parts=[ToolCallPart("write", dict(teaching))])

    class Critic:
        async def complete_review(self, **kwargs):
            nonlocal reviews
            reviews += 1
            result = _review_payload()
            if reviews <= 4:
                result["checks"][6].update(
                    severity="critical",
                    summary=f"Repair remaining criterion {reviews}.",
                    target_ids=["derive-conclusion"],
                    supporting_anchors=[{"source_path": "lecture-01.md", "excerpt": "evidence"}],
                )
            return result

    planner = PracticeDesignPlanner(
        provider_registry=_Registry(), model=FunctionModel(respond), review_client=Critic()
    )
    arguments = dict(
        planner=planner,
        root=tmp_path,
        authorize=lambda: None,
        source=source,
        source_revision="a" * 64,
        allowed_source_paths=("lecture-01.md",),
        initial=None,
        protected_intent=intent,
        repair_context=None,
    )
    if disconnect is True:
        with pytest.raises(RuntimeError, match="connection interrupted"):
            await run_implementation_repair(**arguments)
        saved = json.loads(next(tmp_path.glob("*/draft.json")).read_text())
        assert saved["targets"]["derive-conclusion"]["evidence_criteria"][0]["description"] == (
            "Explain the evidence, revision 0."
        )
    if disconnect == "budget":
        from lecturepilot.model_client import ModelExecutionError

        monkeypatch.setattr("lecturepilot.teaching_design_job.IMPLEMENTATION_MODEL_TURN_LIMIT", 2)
        with pytest.raises(ModelExecutionError, match="current targets and review are saved"):
            await run_implementation_repair(**arguments)
        assert json.loads(next(tmp_path.glob("*/draft.json")).read_text())["review"]
        monkeypatch.setattr("lecturepilot.teaching_design_job.IMPLEMENTATION_MODEL_TURN_LIMIT", 40)
    result = await run_implementation_repair(**arguments)
    intent.require_matches(result.proposal)
    assert list(tmp_path.glob("*/session.json"))
    assert reviews == 5
    assert not any(c.severity == "critical" for c in result.review.checks)
    metrics = json.loads(next(tmp_path.glob("*/session.json")).read_text())["metrics"]
    assert metrics["repair_edits"] == 4
    assert metrics["quality_reviews"] == 5
    assert metrics["resumes"] == int(bool(disconnect))
