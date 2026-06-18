from __future__ import annotations

import json
import sys
from types import SimpleNamespace

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_planner import CourseCanvasPlanner, LiteLLMCoursePlanClient
from lecturepilot.providers import ProviderRegistry


async def test_litellm_course_plan_client_requests_canvas_schema(monkeypatch) -> None:
    calls = []
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"title": "T", "sections": []})))]
        )

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))

    payload = await LiteLLMCoursePlanClient().complete_plan(
        settings=ProviderRegistry.from_env("gemini/test-model").require_ready([]),
        messages=[{"role": "user", "content": "Draft"}],
    )

    assert payload["title"] == "T"
    assert calls[0]["response_format"]["type"] == "json_schema"
    schema = calls[0]["response_format"]["json_schema"]["schema"]
    assert calls[0]["response_format"]["json_schema"]["strict"] is True
    assert schema["required"] == ["title", "sections"]


async def test_course_planner_restyles_source_evidence(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    planner = CourseCanvasPlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=_FakePlanClient(),
    )

    document = await planner.plan_canvas(_source_document())

    assert document.source_kind == "generated"
    assert document.source_ref == "course planner from Lecture03-eng.tex"
    assert document.title == "Bayes as a decision workflow"
    section = document.sections[0]
    assert section.title == "Evidence, update, decision"
    assert section.blocks[0].asset_path.startswith("generated-slides/")
    assert [block.type for block in section.blocks[1:]] == [
        "paragraph",
        "math",
        "asset",
        "video",
        "list",
        "callout",
    ]
    assert section.blocks[3].asset_path == "Ch3/venn.pdf"
    assert section.blocks[3].asset_url == "/course-assets/martius-ml/lecture-03/Ch3/venn.pdf"
    assert section.blocks[4].asset_path == "videos/bayes-risk.mp4"
    assessment_sections = [
        item.id
        for item in document.sections
        if any(block.type in {"checkpoint", "quiz"} for block in item.blocks)
    ]
    assert assessment_sections == ["text-preprocessing-pipeline", "learning-topic-6", "learning-topic-8"]
    middle_checkpoint = next(block for block in document.sections[2].blocks if block.type == "checkpoint")
    assert middle_checkpoint.caption == "Quality gate"
    final_quiz = next(block for block in document.sections[-1].blocks if block.type == "quiz")
    assert final_quiz.answer_index == 0
    assert final_quiz.items[0].startswith("The concept controls")
    assert all(block.asset_path != "unseen.png" for block in section.blocks)
    text_pipeline = next(item for item in document.sections if item.id == "text-preprocessing-pipeline")
    assert text_pipeline.blocks[0].text.startswith("Tokenization turns raw email text into tokens.")
    assert "###" not in text_pipeline.blocks[0].text
    assert "{'type'" not in text_pipeline.blocks[0].text
    assert text_pipeline.blocks[1].items == ["Lowercase words.", "Remove endings."]


class _FakePlanClient:
    async def complete_plan(self, *, settings, messages):
        assert settings.model == "gemini/test-model"
        system_prompt = messages[0]["content"]
        assert "original slide" in system_prompt.lower()
        assert "pdf page" in system_prompt.lower()
        evidence = messages[1]["content"]
        assert "Slide dump" in evidence
        assert "asset_path=Ch3/venn.pdf" in evidence
        assert "original slide id=original-slide-001" in evidence
        assert "video id=frame-1-video" in evidence
        base_section = {
            "id": "bayes-decision-workflow",
            "title": "Evidence, update, decision",
            "source_ref": "Lecture03-eng.tex frames 1, 2, 3",
            "blocks": [
                {
                    "type": "paragraph",
                    "text": (
                        "Evidence updates a prior into a posterior before risk changes the action. "
                        "The learner first identifies the observed signal, then asks how likely "
                        "that signal would be under each class, and only then compares the resulting "
                        "posterior probabilities with the decision costs."
                    ),
                },
                {
                    "type": "math",
                    "text": "P(C \\mid x)=\\frac{P(x \\mid C)P(C)}{P(x)}",
                },
                {
                    "type": "asset",
                    "asset_path": "Ch3/venn.pdf",
                    "caption": "Venn diagram from the lecture source",
                },
                {
                    "type": "asset",
                    "asset_path": "unseen.png",
                    "caption": "This unsupported asset must be ignored",
                },
                {
                    "type": "video",
                    "asset_path": "videos/bayes-risk.mp4",
                    "caption": "Professor walkthrough clip",
                    "text": "Short local video showing the Bayes-risk workflow.",
                },
                {
                    "type": "list",
                    "items": [
                        "Start from the prior belief before seeing the measurement.",
                        "Use the likelihood to score how compatible the evidence is with each class.",
                        "Normalize with the evidence term so the posterior can be compared.",
                    ],
                },
                {
                    "type": "callout",
                    "text": (
                        "Infographic brief: show prior, likelihood, posterior, and decision risk as "
                        "a left-to-right workflow so the student can trace where each number enters. "
                        "The learner should be able to point at the canvas and explain which source "
                        "quantity changes after observation and which quantity is a fixed modeling choice."
                    ),
                },
            ],
        }
        extra_sections = [
            {
                "id": f"learning-topic-{index}",
                "title": f"Planner section {index}",
                "source_ref": "Lecture03-eng.tex frame 1",
                "blocks": [
                    {
                        "type": "paragraph",
                        "text": (
                            f"Source-grounded explanation {index} connects the lecture claim to the "
                            "mathematical object the student sees on the slide. It gives enough context "
                            "to read the section independently before the tutor starts asking checks."
                        ),
                    },
                    {
                        "type": "paragraph",
                        "text": (
                            f"Step-by-step mechanism {index} explains what is computed first, what "
                            "changes after observing evidence, and why the final decision can differ. "
                            "The explanation is deliberately longer than a slide bullet so the learner "
                            "can follow the reasoning without needing the original lecture narration."
                        ),
                    },
                    {
                        "type": "list",
                        "items": [
                            f"Identify the relevant variable for topic {index}.",
                            "Compute the probability or risk term from the source formula and state what each symbol means.",
                            "Interpret the result as a modeling decision, including what would change in a failure case.",
                        ],
                    },
                    {
                        "type": "callout",
                        "text": (
                            f"Worked example checkpoint {index}: ask the learner to transfer the "
                            "formula to a small classification case before moving on. The example is "
                            "grounded in the source section and prepares a later quality gate."
                        ),
                    },
                ],
            }
            for index in range(2, 9)
        ]
        extra_sections[1] = {
            "id": "text-preprocessing-pipeline",
            "title": "Text preprocessing pipeline",
            "source_ref": "Lecture03-eng.tex frames 24, 25",
            "blocks": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": (
                                "### Tokenization turns raw email text into tokens. This matters because the "
                                "classifier never sees the original message as prose; it sees a controlled "
                                "sequence of units that can be counted and compared across classes."
                            ),
                        }
                    ],
                },
                {
                    "type": "list",
                    "content": [
                        {"type": "paragraph", "content": "Lowercase words."},
                        {"type": "paragraph", "content": "Remove endings."},
                    ],
                },
                {
                    "type": "paragraph",
                    "text": (
                        "After tokenization, preprocessing reduces variation that is irrelevant for the "
                        "classification decision. Words such as Email and email should not become two "
                        "different pieces of evidence unless capitalization itself is part of the model."
                    ),
                },
                {
                    "type": "callout",
                    "text": (
                        "A useful learner check is to take one short spam sentence and identify which "
                        "tokens remain after lowercasing, stemming, and stop-word removal. This connects "
                        "the source slides to the later probability estimates used by Naive Bayes."
                    ),
                },
            ],
        }
        return {
            "title": "Bayes as a decision workflow",
            "sections": [base_section, *extra_sections],
        }


def _source_document() -> CanvasDocument:
    source_sections = [
        CanvasSection(
            id="evidence-update-decision",
            title="Slide dump",
            source_ref="frame 1",
            blocks=[
                CanvasBlock(id="frame-1-list", type="list", items=["prior", "likelihood", "posterior"]),
                CanvasBlock(id="frame-1-math", type="math", text="P(C|x)=..."),
                CanvasBlock(
                    id="frame-1-asset",
                    type="asset",
                    asset_path="Ch3/venn.pdf",
                    asset_url="/course-assets/martius-ml/lecture-03/Ch3/venn.pdf",
                    caption="Venn diagram",
                ),
                CanvasBlock(
                    id="original-slide-001",
                    type="asset",
                    asset_path="generated-slides/lecture-03/Lecture03-eng/slide-001.png",
                    asset_url="/course-assets/martius-ml/lecture-03/generated-slides/lecture-03/Lecture03-eng/slide-001.png",
                    caption="Original slide 1 from Lecture03-eng.pdf",
                ),
                CanvasBlock(
                    id="original-slide-002",
                    type="asset",
                    asset_path="generated-slides/lecture-03/Lecture03-eng/slide-002.png",
                    asset_url="/course-assets/martius-ml/lecture-03/generated-slides/lecture-03/Lecture03-eng/slide-002.png",
                    caption="Original slide 2 from Lecture03-eng.pdf",
                ),
                CanvasBlock(
                    id="frame-1-video",
                    type="video",
                    asset_path="videos/bayes-risk.mp4",
                    asset_url="/course-assets/martius-ml/lecture-03/videos/bayes-risk.mp4",
                    caption="Professor walkthrough clip",
                ),
            ],
        )
    ]
    source_sections.extend(
        CanvasSection(
            id=f"source-section-{index}",
            title=f"Source section {index}",
            source_ref=f"frame {index}",
            blocks=[CanvasBlock(id=f"source-section-{index}-p", type="paragraph", text="Source detail.")],
        )
        for index in range(2, 9)
    )
    return CanvasDocument(
        id="martius-ml-lecture-03",
        course_id="martius-ml",
        lecture_id="lecture-03",
        title="Slide dump",
        source_kind="latex",
        source_ref="Lecture03-eng.tex",
        workspace_path="source.json",
        sections=source_sections,
    )
