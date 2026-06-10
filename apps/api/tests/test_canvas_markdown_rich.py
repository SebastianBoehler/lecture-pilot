from pathlib import Path

from lecturepilot.canvas_markdown import read_document_source


def test_canvas_markdown_parses_rich_learning_blocks(tmp_path: Path) -> None:
    canvas_dir = tmp_path / "canvas"
    sections_dir = canvas_dir / "sections"
    sections_dir.mkdir(parents=True)
    (canvas_dir / "index.md").write_text(
        """---
id: "martius-ml-lecture-03"
import_version: 3
course_id: "martius-ml"
lecture_id: "lecture-03"
title: "Bayesian Decision Theory"
source_kind: "generated"
source_ref: "Lecture03-eng.tex"
---
""",
        encoding="utf-8",
    )
    (sections_dir / "01-risk.md").write_text(
        """---
id: "risk-decisions"
title: "Risk decisions"
source_ref: "Lecture03-eng.tex frames 33-38"
---

Longer narrative paragraph with **expected risk** and enough context for the learner.

![Expected risk plot](https://example.test/risk-plot.png)

[Bayesian decision theory recap](https://youtu.be/12345678901)

| Action | Cost focus |
| --- | --- |
| Reject | Avoid unsafe guesses |
| Classify | Minimize expected loss |

:::checkpoint Risk gate
Explain why a costly false negative can lower the decision threshold.
:::

:::quiz Threshold check
Which quantity changes when false negatives are ten times costlier?
- Prior probability
- [x] Loss term
- Evidence normalizer
:::

:::component risk-threshold-check
{
  "id": "risk-threshold-check",
  "type": "single_choice_quiz",
  "title": "Risk threshold component",
  "prompt": "Which action should minimize cost-sensitive risk?",
  "options": [
    {"id": "A", "text": "Choose the lowest expected risk", "correct": true},
    {"id": "B", "text": "Always choose the highest posterior", "correct": false}
  ]
}
:::
""",
        encoding="utf-8",
    )

    document = read_document_source(canvas_dir)
    blocks = document.sections[0].blocks

    assert [block.type for block in blocks] == [
        "paragraph",
        "asset",
        "video",
        "table",
        "checkpoint",
        "quiz",
        "component",
    ]
    assert blocks[1].asset_path is None
    assert blocks[1].asset_url == "https://example.test/risk-plot.png"
    assert blocks[2].caption == "Bayesian decision theory recap"
    assert blocks[3].text and "| Action | Cost focus |" in blocks[3].text
    assert blocks[4].caption == "Risk gate"
    assert "false negative" in (blocks[4].text or "")
    assert blocks[5].caption == "Threshold check"
    assert blocks[5].items == ["Prior probability", "Loss term", "Evidence normalizer"]
    assert blocks[5].answer_index == 1
    assert blocks[6].component_id == "risk-threshold-check"
    assert blocks[6].component_type == "single_choice_quiz"
    assert blocks[6].caption == "Risk threshold component"
    assert blocks[6].items == ["Choose the lowest expected risk", "Always choose the highest posterior"]
    assert blocks[6].answer_index == 0
