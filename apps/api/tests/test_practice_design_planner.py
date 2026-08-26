from types import SimpleNamespace
import sys

import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.models import ProviderCapability, ProviderSettings


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
async def test_planner_uses_native_schema_and_exact_authoritative_source_paths(monkeypatch) -> None:
    from lecturepilot.course_practice_design_client import LiteLLMPracticeDesignClient
    from lecturepilot.course_practice_design_planner import PracticeDesignPlanner

    calls: list[dict] = []

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            '{"lecture_title":"Bayes rule","objective":"Calculate a posterior '
                            'from stated evidence.","targets":[{"id":"posterior","title":"Posterior",'
                            '"outcome":"Calculate a posterior from stated evidence.","baseline_task":'
                            '"Calculate the posterior for the stated prior and likelihood.",'
                            '"target_invariant":"Apply Bayes rule to the stated prior and likelihood.",'
                            '"independent_exit_task":"Calculate a posterior for a different prior and likelihood.",'
                            '"independent_exit_surface_change":"Change only the stated probabilities.",'
                            '"delayed_transfer_task":"Choose and calculate a posterior for a changed diagnostic setting.",'
                            '"delayed_transfer_surface_change":"Change the scenario and representation, not the rule.",'
                            '"evidence_criteria":[{"id":"substitute","description":"Substitutes the stated values.",'
                            '"required":true}],"misconceptions":[],"hint_ladder":[],"review_after_days":7,'
                            '"source_refs":["lecture.md"]}],"planning_context":{'
                            '"learner_level":null,"prerequisites":null,"time_budget_minutes":null,'
                            '"allowed_aids":null,"assessment_conditions":null,"insufficiencies":['
                            '{"field":"learner_level","description":"The source does not state the learner level."},'
                            '{"field":"prerequisites","description":"The source does not state prerequisites."},'
                            '{"field":"time_budget_minutes","description":"The source does not state a time budget."},'
                            '{"field":"allowed_aids","description":"The source does not state allowed aids."},'
                            '{"field":"assessment_conditions","description":"The source does not state assessment conditions."}]}}'
                        )
                    )
                )
            ],
            usage=None,
        )

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))
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
        provider_registry=Registry(), model_client=LiteLLMPracticeDesignClient()
    )

    proposal = await planner.propose(
        source=_source(), source_revision=SOURCE_REVISION, allowed_source_paths=("lecture.md",)
    )

    assert proposal.targets[0].source_refs == ("lecture.md",)
    assert proposal.planning_context.learner_level is None
    request = calls[0]
    assert request["response_format"]["type"] == "json_schema"
    assert request["response_format"]["json_schema"]["strict"] is True
    instruction = request["messages"][0]["content"]
    assert "minimum set of distinct capabilities supported by the source" in instruction
    assert "3 to 6 targets" not in instruction
    assert "Diagnostic attempt" in instruction
    assert "Independent exit" in instruction
    assert "Delayed transfer" in instruction
    assert "Atomic evidence criteria" in instruction
    assert "prompt asks the learner to inspect or plan" in instruction
    assert "worked_step gives one justified step" in instruction
    assert "not a claim that this interval is scientifically optimal" in instruction
    assert "lecture.md" in request["messages"][1]["content"]
    assert "unrouted.md" not in request["messages"][1]["content"]


def test_response_schema_describes_the_assessment_and_scaffold_contract() -> None:
    from lecturepilot.course_practice_design_prompt import practice_design_response_format

    schema = practice_design_response_format()["json_schema"]["schema"]
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
