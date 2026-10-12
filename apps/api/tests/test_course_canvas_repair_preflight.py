from lecturepilot.course_canvas_math import normalize_generated_math, validate_section_math
from test_course_canvas_math import _section_with_math


def test_generated_math_normalization_removes_stray_display_delimiters() -> None:
    formula = r"\begin{aligned}a &= b \\ \[c &= d\end{aligned}"

    normalized = normalize_generated_math(formula)

    assert normalized == r"\begin{aligned}a &= b \\ c &= d\end{aligned}"
    validate_section_math(_section_with_math(normalized))
