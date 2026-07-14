from __future__ import annotations

import pytest

from lecturepilot.canvas_markdown_blocks import block_to_markdown
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_math import generated_math_instructions, validate_section_math
from lecturepilot.course_canvas_prompt import planner_messages, repair_message
from lecturepilot.course_canvas_section_planner import _section_messages
from lecturepilot.course_canvas_validation import validate_planned_document
from lecturepilot.providers import ProviderConfigurationError


def test_generation_prompts_require_raw_portable_display_math() -> None:
    source = _source_document()

    prompts = [
        planner_messages(source)[0]["content"],
        repair_message("bad math", source)["content"],
        _section_messages(source, source.sections[0])[0]["content"],
        generated_math_instructions(),
    ]

    for prompt in prompts:
        assert "portable KaTeX" in prompt
        assert "raw LaTeX" in prompt
        assert "explanatory prose" in prompt
        assert "aligned" in prompt


def test_clean_aligned_display_equation_is_accepted_unchanged() -> None:
    formula = (
        r"\begin{aligned}"
        "\n"
        r"\mathcal{L}(\theta) &= \frac{1}{n}\sum_{i=1}^{n}(y_i-\hat{y}_i)^2 \\"
        "\n"
        r"\theta^\star &= \operatorname*{arg\,min}_{\theta}\mathcal{L}(\theta)"
        "\n"
        r"\end{aligned}"
    )
    section = _section_with_math(formula)

    validate_section_math(section)

    assert section.blocks[0].text == formula
    markdown = block_to_markdown(section.blocks[0])
    assert markdown.count("```math") == 1
    assert f"```math\n{formula}\n```" in markdown


@pytest.mark.parametrize(
    ("formula", "error"),
    [
        (
            "```math\n" + r"p(y \mid x)=\frac{p(x \mid y)p(y)}{p(x)}" + "\n```",
            "raw LaTeX",
        ),
        (
            r"$\bar{g}_t=\alpha\bar{g}_{t-1}+(1-\alpha)g_t$. "
            "This average emphasizes recent gradients.",
            "raw LaTeX",
        ),
        (
            r"The state-value function is v_\pi(s)=\mathbb{E}[G_t \mid S_t=s].",
            "explanatory prose",
        ),
        (r"z=\mu+\epsilon\N(0,1)", "unsupported or course-specific"),
        (
            r"\newcommand{\Loss}{\mathcal{L}}\Loss(\theta)=0",
            "macro definitions",
        ),
    ],
)
def test_malformed_or_course_specific_math_is_rejected(formula: str, error: str) -> None:
    with pytest.raises(ProviderConfigurationError, match=error):
        validate_section_math(_section_with_math(formula))


@pytest.mark.parametrize(
    ("formula", "error"),
    [
        (r"\frac{1}{n", "unbalanced braces"),
        (r"\begin{aligned} x &= y", r"unmatched \\begin\{aligned\}"),
        (
            r"\begin{aligned}\begin{matrix}x\end{aligned}\end{matrix}",
            "environment nesting must match",
        ),
    ],
)
def test_structurally_invalid_math_is_rejected(formula: str, error: str) -> None:
    with pytest.raises(ProviderConfigurationError, match=error):
        validate_section_math(_section_with_math(formula))


@pytest.mark.parametrize(
    "formula",
    [
        r"\frac{\{x\}}{1 + \sqrt{y}}",
        r"\begin{aligned}A &= \begin{pmatrix}1 & 0 \\ 0 & 1\end{pmatrix} \\ x &= y\end{aligned}",
    ],
)
def test_structurally_valid_math_is_accepted(formula: str) -> None:
    validate_section_math(_section_with_math(formula))


def test_planned_document_validation_rejects_prose_in_math_blocks() -> None:
    document = _valid_generated_document()
    document.sections[0].blocks[0] = CanvasBlock(
        id="topic-1-math",
        type="math",
        text=(
            r"The loss is minimized by "
            r"\theta^*=\operatorname*{arg\,min}_\theta \mathcal{L}(\theta)."
        ),
    )

    with pytest.raises(ProviderConfigurationError, match="topic-1-math.*explanatory prose"):
        validate_planned_document(document, _source_document())


def _section_with_math(formula: str) -> CanvasSection:
    return CanvasSection(
        id="risk-minimization",
        title="Risk minimization",
        source_ref="Lecture02.tex frame 8",
        blocks=[CanvasBlock(id="risk-equation", type="math", text=formula)],
    )


def _source_document() -> CanvasDocument:
    return CanvasDocument(
        id="course-lecture-source",
        course_id="course",
        lecture_id="lecture-02",
        title="Learning theory",
        source_kind="latex",
        source_ref="Lecture02.tex",
        workspace_path="source.json",
        sections=[
            CanvasSection(
                id="source-risk",
                title="Risk",
                source_ref="Lecture02.tex frame 8",
                blocks=[CanvasBlock(id="source-risk-p", type="paragraph", text="Risk source")],
            )
        ],
    )


def _valid_generated_document() -> CanvasDocument:
    sections = []
    for index in range(1, 6):
        blocks = [
            CanvasBlock(
                id=f"topic-{index}-math",
                type="math",
                text=r"\mathcal{L}(\theta)=\frac{1}{n}\sum_{i=1}^{n}\ell_i(\theta)",
            ),
            CanvasBlock(id=f"topic-{index}-p-1", type="paragraph", text="A" * 240),
            CanvasBlock(id=f"topic-{index}-p-2", type="paragraph", text="B" * 240),
            CanvasBlock(id=f"topic-{index}-p-3", type="paragraph", text="C" * 240),
        ]
        if index in {2, 4}:
            blocks.append(
                CanvasBlock(
                    id=f"topic-{index}-checkpoint",
                    type="checkpoint",
                    text="Explain the calculation.",
                )
            )
        if index in {3, 5}:
            blocks.append(
                CanvasBlock(
                    id=f"topic-{index}-quiz",
                    type="quiz",
                    text="Which expression is the loss?",
                    items=["The first", "The second"],
                    answer_index=0,
                )
            )
        sections.append(
            CanvasSection(
                id=f"topic-{index}",
                title=f"Topic {index}",
                source_ref=f"Lecture02.tex frame {index}",
                blocks=blocks,
            )
        )
    return CanvasDocument(
        id="course-lecture-generated",
        course_id="course",
        lecture_id="lecture-02",
        title="Learning theory",
        source_kind="generated",
        source_ref="course planner from Lecture02.tex",
        workspace_path="draft.json",
        sections=sections,
    )
