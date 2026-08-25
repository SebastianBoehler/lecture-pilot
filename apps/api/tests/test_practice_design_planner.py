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
                            '"independent_exit_task":"Calculate a posterior for a different prior and likelihood.",'
                            '"delayed_transfer_task":"Choose and calculate a posterior for a changed diagnostic setting.",'
                            '"evidence_criteria":[{"id":"substitute","description":"Substitutes the stated values.",'
                            '"required":true}],"misconceptions":[],"hint_ladder":[],"review_after_days":7,'
                            '"source_refs":["lecture.md"]}]}'
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
    request = calls[0]
    assert request["response_format"]["type"] == "json_schema"
    assert request["response_format"]["json_schema"]["strict"] is True
    assert "3 to 6 targets when the evidence supports them" in request["messages"][0]["content"]
    assert "lecture.md" in request["messages"][1]["content"]
    assert "unrouted.md" not in request["messages"][1]["content"]
