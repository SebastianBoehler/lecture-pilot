from __future__ import annotations

import re

from lecturepilot.practice_exam_models import PracticeExamPublic


_ESCAPES = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "%": r"\%",
    "$": r"\$",
    "&": r"\&",
    "_": r"\_",
    "#": r"\#",
    "^": r"\textasciicircum{}",
    "~": r"\textasciitilde{}",
}
_ALLOWED_MATH_COMMANDS = frozenset(
    {
        "Delta",
        "Gamma",
        "Lambda",
        "Omega",
        "Phi",
        "Pi",
        "Psi",
        "Sigma",
        "Theta",
        "alpha",
        "approx",
        "argmax",
        "argmin",
        "beta",
        "cap",
        "cdot",
        "chi",
        "cup",
        "delta",
        "div",
        "ell",
        "epsilon",
        "eta",
        "exp",
        "frac",
        "gamma",
        "ge",
        "in",
        "infty",
        "kappa",
        "lambda",
        "le",
        "left",
        "ln",
        "log",
        "lVert",
        "mapsto",
        "mathbb",
        "mathbf",
        "mathcal",
        "mathrm",
        "max",
        "mid",
        "min",
        "mp",
        "mu",
        "nabla",
        "neq",
        "notin",
        "omega",
        "operatorname",
        "partial",
        "phi",
        "pi",
        "pm",
        "prod",
        "psi",
        "quad",
        "qquad",
        "rho",
        "right",
        "rVert",
        "sigma",
        "sqrt",
        "subset",
        "sum",
        "supset",
        "tau",
        "text",
        "theta",
        "times",
        "to",
        "varepsilon",
        "varphi",
        "vert",
        "xi",
        "zeta",
    }
)
_ALLOWED_MATH_ENVIRONMENTS = frozenset({"aligned", "bmatrix", "cases", "matrix", "pmatrix"})
_MATH_COMMAND = re.compile(r"\\([A-Za-z]+|.)")
_MATH_ENVIRONMENT = re.compile(r"\\(begin|end)\{([^{}]+)\}")


def render_practice_exam_tex(
    exam: PracticeExamPublic,
    *,
    include_markup: bool = True,
) -> str:
    lines = [
        r"\documentclass[11pt,a4paper]{article}",
        r"\usepackage[margin=2.2cm]{geometry}",
        r"\usepackage{amsmath}",
        r"\usepackage{amssymb}",
        r"\usepackage{fancyhdr}",
        r"\setlength{\parindent}{0pt}",
        r"\setlength{\headheight}{14pt}",
        r"\pagestyle{fancy}",
        r"\fancyhf{}",
        rf"\lhead{{{escape_tex(exam.title)}}}",
        rf"\rhead{{{exam.duration_minutes} min · {exam.total_points} points}}",
        r"\cfoot{\thepage}",
        r"\begin{document}",
        rf"\section*{{{escape_tex(exam.title)}}}",
        rf"\textbf{{Duration:}} {exam.duration_minutes} minutes\quad "
        rf"\textbf{{Total:}} {exam.total_points} points",
        r"\vspace{0.5em}",
        r"\hrule",
        r"\vspace{0.8em}",
    ]
    for instruction in exam.instructions:
        lines.append(
            rf"\textbullet\ {_render_text(instruction, include_markup=include_markup)}\par"
        )
    for index, question in enumerate(exam.questions, start=1):
        lines.extend(
            [
                r"\vspace{1em}",
                r"\noindent\begin{minipage}{\textwidth}",
                rf"\subsection*{{Question {index} \hfill {question.points} points}}",
                _render_text(question.prompt, include_markup=include_markup) + r"\par",
                r"\vspace{0.6em}",
            ]
        )
        if question.status == "invalid":
            pass
        elif question.kind == "multiple_choice":
            for option in question.options:
                lines.append(
                    rf"$\square$\quad {_render_text(option, include_markup=include_markup)}\par\vspace{{0.35em}}"
                )
        else:
            answer_space = min(8.0, max(2.5, question.points * 0.8))
            lines.append(rf"\vspace{{{answer_space:.1f}cm}}")
            lines.append(r"\hrule")
        lines.append(r"\end{minipage}")
    lines.extend([r"\end{document}", ""])
    return "\n".join(lines)


def escape_tex(value: str) -> str:
    return "".join(_ESCAPES.get(character, character) for character in value).replace(
        "\n", r"\par "
    )


def render_exam_markup(value: str) -> str:
    output: list[str] = []
    cursor = 0
    while cursor < len(value):
        if value.startswith("`", cursor):
            cursor = _render_delimited(value, cursor, "`", r"\texttt{%s}", output)
        elif value.startswith("$$", cursor):
            cursor = _render_math(value, cursor, "$$", output, display=True)
        elif value.startswith("$", cursor):
            cursor = _render_math(value, cursor, "$", output, display=False)
        elif value.startswith("**", cursor):
            cursor = _render_delimited(value, cursor, "**", r"\textbf{%s}", output)
        elif value.startswith("*", cursor):
            cursor = _render_delimited(value, cursor, "*", r"\emph{%s}", output)
        else:
            next_marker = min(
                (
                    position
                    for marker in ("`", "$", "*")
                    if (position := value.find(marker, cursor)) >= 0
                ),
                default=len(value),
            )
            output.append(escape_tex(value[cursor:next_marker]))
            cursor = next_marker
    return "".join(output)


def _render_text(value: str, *, include_markup: bool) -> str:
    if include_markup:
        return render_exam_markup(value)
    return escape_tex(value)


def _render_delimited(
    value: str,
    cursor: int,
    delimiter: str,
    template: str,
    output: list[str],
) -> int:
    end = value.find(delimiter, cursor + len(delimiter))
    if end < 0 or end == cursor + len(delimiter):
        output.append(escape_tex(delimiter))
        return cursor + len(delimiter)
    content = value[cursor + len(delimiter) : end]
    rendered = escape_tex(content) if delimiter == "`" else render_exam_markup(content)
    output.append(template % rendered)
    return end + len(delimiter)


def _render_math(
    value: str,
    cursor: int,
    delimiter: str,
    output: list[str],
    *,
    display: bool,
) -> int:
    end = value.find(delimiter, cursor + len(delimiter))
    if end < 0 or end == cursor + len(delimiter):
        output.append(escape_tex(delimiter))
        return cursor + len(delimiter)
    expression = value[cursor + len(delimiter) : end]
    raw = value[cursor : end + len(delimiter)]
    if not _safe_math(expression):
        output.append(escape_tex(raw))
    elif display:
        output.append(r"\[" + expression.strip() + r"\]")
    else:
        output.append("$" + expression.strip() + "$")
    return end + len(delimiter)


def _safe_math(expression: str) -> bool:
    if not expression.strip() or any(character in expression for character in "$#%~\x00"):
        return False
    if not _balanced_braces(expression):
        return False
    environments = _MATH_ENVIRONMENT.findall(expression)
    if any(name not in _ALLOWED_MATH_ENVIRONMENTS for _, name in environments):
        return False
    if not _balanced_environments(environments):
        return False
    commands = _MATH_COMMAND.findall(_MATH_ENVIRONMENT.sub("", expression))
    return all(
        command in _ALLOWED_MATH_COMMANDS or command in {"\\", ",", ";", "!", " "}
        for command in commands
    )


def _balanced_environments(environments: list[tuple[str, str]]) -> bool:
    stack: list[str] = []
    for action, name in environments:
        if action == "begin":
            stack.append(name)
        elif not stack or stack.pop() != name:
            return False
    return not stack


def _balanced_braces(value: str) -> bool:
    depth = 0
    for character in value:
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0
