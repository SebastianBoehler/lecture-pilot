import pytest
from pydantic_ai.models.function import FunctionModel

from authoring_test_helpers import markdown
from lecturepilot.authoring_job import run_authoring_job
from lecturepilot.canvas_inline_code_math import latex_in_inline_code
from test_authoring_job import VALID, authoring_job


@pytest.mark.parametrize(
    ("text", "span"),
    [
        ("Digits use `y \\in \\{0, \\ldots, 9\\}`.", "y \\in \\{0, \\ldots, 9\\}"),
        ("The rate is `\\alpha`.", "\\alpha"),
        ('Print with `print("a\\nb")` or call `h(x) = y`.', None),
        ("A fence ```python\nx = 1\n``` is not inline code.", None),
        ("Proper math: $y \\in \\{0, 1\\}$.", None),
    ],
)
def test_only_inline_code_holding_latex_counts_as_misplaced_math(text, span) -> None:
    assert latex_in_inline_code(text) == span


async def test_math_written_as_inline_code_is_repaired_by_the_section_author(tmp_path):
    job = authoring_job(tmp_path)
    outputs = iter(
        [
            VALID
            + '\n<!-- block id="labels" type="paragraph" -->\nLabels are `y \\in \\{0, 1\\}`.\n',
            VALID
            + '\n<!-- block id="labels" type="paragraph" -->\nLabels are $y \\in \\{0, 1\\}$.\n',
        ]
    )
    result = await run_authoring_job(job, model=FunctionModel(lambda m, i: markdown(next(outputs))))

    assert result.document.sections[0].blocks[-1].text == "Labels are $y \\in \\{0, 1\\}$."
    assert result.metrics.validation_failures == 1
