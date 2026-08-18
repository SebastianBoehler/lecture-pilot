from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_quality import LiteLLMCanvasQualityClient, _quality_messages
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.providers import ProviderRegistry


async def test_quality_review_does_not_impose_an_output_token_cap(monkeypatch) -> None:
    calls: list[dict] = []
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(content=json.dumps({"issues": []})),
                )
            ]
        )

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))
    document = _document()

    payload = await LiteLLMCanvasQualityClient().complete_review(
        settings=ProviderRegistry.from_env("openai/gpt-5.6-luna").require_ready([]),
        source_document=document,
        candidate_document=document,
    )

    assert payload == {"issues": []}
    assert "max_tokens" not in calls[0]
    assert calls[0]["reasoning_effort"] == "low"


async def test_quality_review_retries_an_empty_truncated_response(monkeypatch) -> None:
    calls: list[dict] = []
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 2:
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        message=SimpleNamespace(content=json.dumps({"issues": []})),
                    )
                ]
            )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="length",
                    message=SimpleNamespace(content=None, refusal=None),
                )
            ]
        )

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))
    document = _document()

    payload = await LiteLLMCanvasQualityClient().complete_review(
        settings=ProviderRegistry.from_env("openai/gpt-5.6-luna").require_ready([]),
        source_document=document,
        candidate_document=document,
    )

    assert payload == {"issues": []}
    assert len(calls) == 2


async def test_quality_review_reports_repeated_invalid_responses(monkeypatch) -> None:
    calls: list[dict] = []
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="length",
                    message=SimpleNamespace(content=None, refusal=None),
                )
            ]
        )

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))
    document = _document()

    with pytest.raises(
        ModelExecutionError,
        match=r"Canvas quality review returned an empty response \(finish_reason=length\)",
    ):
        await LiteLLMCanvasQualityClient().complete_review(
            settings=ProviderRegistry.from_env("openai/gpt-5.6-luna").require_ready([]),
            source_document=document,
            candidate_document=document,
        )

    assert len(calls) == 2


async def test_quality_review_preserves_a_provider_timeout_message(monkeypatch) -> None:
    calls = 0
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    async def fake_completion(**_kwargs):
        nonlocal calls
        calls += 1
        raise TimeoutError("provider timeout")

    async def no_wait(_seconds: float) -> None:
        return None

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))
    monkeypatch.setattr("lecturepilot.model_usage.asyncio.sleep", no_wait)
    document = _document()

    with pytest.raises(ModelExecutionError, match="timed out"):
        await LiteLLMCanvasQualityClient().complete_review(
            settings=ProviderRegistry.from_env("openai/gpt-5.6-luna").require_ready([]),
            source_document=document,
            candidate_document=document,
        )

    assert calls == 1


def test_quality_review_prompt_is_bounded_to_claims_and_relevant_evidence() -> None:
    source = _document_with_large_sections(source_kind="latex")
    candidate = _document_with_large_sections(source_kind="generated")

    messages = _quality_messages(source, candidate)
    prompt = messages[1]["content"]

    assert len(prompt) <= 20_000
    assert "CANDIDATE SECTION topic-1" in prompt
    assert "SOURCE EVIDENCE lecture.pdf page 1" in prompt
    assert '"workspace_path"' not in prompt


def _document() -> CanvasDocument:
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
                blocks=[CanvasBlock(id="claim", type="paragraph", text="A source claim.")],
            )
        ],
    )


def _document_with_large_sections(*, source_kind: str) -> CanvasDocument:
    return CanvasDocument(
        id="course-lecture",
        course_id="course",
        lecture_id="lecture",
        title="Lecture",
        source_kind=source_kind,
        source_ref="lecture.pdf",
        workspace_path="private/canvas/index.md",
        sections=[
            CanvasSection(
                id=f"topic-{index}",
                title=f"Topic {index}",
                source_ref=f"lecture.pdf page {index}",
                blocks=[
                    CanvasBlock(
                        id=f"claim-{index}",
                        type="paragraph",
                        text=(f"Evidence {index} " + "grounded detail " * 1_000),
                    )
                ],
            )
            for index in range(1, 6)
        ],
    )
