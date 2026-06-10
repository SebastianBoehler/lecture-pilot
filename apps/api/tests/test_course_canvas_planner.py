from __future__ import annotations

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_planner import CourseCanvasPlanner
from lecturepilot.providers import ProviderRegistry


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
    assert [block.type for block in section.blocks] == [
        "paragraph",
        "math",
        "asset",
        "callout",
    ]
    assert section.blocks[2].asset_path == "Ch3/venn.pdf"
    assert section.blocks[2].asset_url == "/course-assets/martius-ml/lecture-03/Ch3/venn.pdf"
    middle_checkpoint = next(block for block in document.sections[3].blocks if block.type == "checkpoint")
    assert middle_checkpoint.caption == "Quality gate"
    final_quiz = next(block for block in document.sections[-1].blocks if block.type == "quiz")
    assert final_quiz.answer_index == 0
    assert final_quiz.items[0].startswith("The concept controls")
    assert all(block.asset_path != "unseen.png" for block in section.blocks)


class _FakePlanClient:
    async def complete_plan(self, *, settings, messages):
        assert settings.model == "gemini/test-model"
        evidence = messages[1]["content"]
        assert "Slide dump" in evidence
        assert "asset_path=Ch3/venn.pdf" in evidence
        base_section = {
            "id": "bayes-decision-workflow",
            "title": "Evidence, update, decision",
            "source_ref": "Lecture03-eng.tex frames 1, 2, 3",
            "blocks": [
                {
                    "type": "paragraph",
                    "text": "Evidence updates a prior into a posterior before risk changes the action.",
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
                    "type": "callout",
                    "text": "Infographic brief: show prior, likelihood, posterior, and decision risk.",
                },
            ],
        }
        extra_sections = [
            {
                "id": f"learning-topic-{index}",
                "title": f"Planner section {index}",
                "source_ref": "Lecture03-eng.tex frame 1",
                "blocks": [
                    {"type": "paragraph", "text": f"Source-grounded explanation {index}."},
                    {"type": "callout", "text": f"Worked example checkpoint {index}."},
                ],
            }
            for index in range(2, 9)
        ]
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
