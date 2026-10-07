from __future__ import annotations

import json


from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_quality import NativeCanvasQualityClient, _quality_messages


async def test_quality_review_native_schema_has_output_cap_and_critic_reasoning():
    from pydantic_ai.messages import ModelResponse, TextPart
    from pydantic_ai.models.function import FunctionModel
    from lecturepilot.models import ProviderSettings

    calls = []

    def respond(messages, info):
        calls.append(info)
        return ModelResponse(parts=[TextPart('{"issues": []}')])

    settings = ProviderSettings(
        provider="openai", model="openai/gpt-6", api_key_env="OPENAI_API_KEY", capabilities=set()
    )
    document = _document()
    payload = await NativeCanvasQualityClient(model=FunctionModel(respond)).complete_review(
        settings=settings,
        source_document=document,
        candidate_document=document,
    )
    assert payload == {"issues": []}
    assert calls[0].model_settings["max_tokens"] == 16_000
    assert calls[0].model_settings["openai_reasoning_effort"] == "medium"


async def test_quality_review_native_schema_repairs_unknown_coordinates():
    from pydantic_ai.messages import ModelResponse, TextPart
    from pydantic_ai.models.function import FunctionModel
    from lecturepilot.models import ProviderSettings

    calls = 0

    def respond(messages, info):
        nonlocal calls
        calls += 1
        payload = (
            {"issues": [{"section_id": "unknown", "block_id": None, "reason": "Claim"}]}
            if calls == 1
            else {"issues": []}
        )
        return ModelResponse(parts=[TextPart(json.dumps(payload))])

    settings = ProviderSettings(
        provider="openai", model="openai/gpt-6", api_key_env="OPENAI_API_KEY", capabilities=set()
    )
    document = _document()
    assert await NativeCanvasQualityClient(model=FunctionModel(respond)).complete_review(
        settings=settings,
        source_document=document,
        candidate_document=document,
    ) == {"issues": []}
    assert calls == 2


def test_quality_review_prompt_is_bounded_to_claims_and_relevant_evidence() -> None:
    source = _document_with_large_sections(source_kind="latex")
    candidate = _document_with_large_sections(source_kind="generated")

    messages = _quality_messages(source, candidate)
    prompt = messages[1]["content"]

    assert len(prompt) <= 20_000
    assert "CANDIDATE SECTION topic-1" in prompt
    assert "SOURCE EVIDENCE lecture.pdf page 1" in prompt
    assert '"workspace_path"' not in prompt


def test_quality_review_prompt_never_clips_a_candidate_line_mid_expression() -> None:
    source = _document()
    candidate = source.model_copy(
        update={
            "sections": [
                source.sections[0].model_copy(
                    update={
                        "blocks": [
                            *[
                                CanvasBlock(
                                    id=f"filler-{index}",
                                    type="paragraph",
                                    text="grounded detail " * 180,
                                )
                                for index in range(6)
                            ],
                            CanvasBlock(
                                id="decision-rule",
                                type="math",
                                text=r"P(x\mid C=1)P(C=1) > P(x\mid C=0)P(C=0)",
                            ),
                        ]
                    }
                )
            ]
        }
    )

    prompt = _quality_messages(source, candidate)[1]["content"]

    assert "P(x\\mid C=0)P(C\n" not in prompt
    assert "P(x\\mid C=0)P(C=0)" in prompt or "decision-rule" not in prompt


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
