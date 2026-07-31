from __future__ import annotations

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


def render_practice_exam_tex(exam: PracticeExamPublic) -> str:
    lines = [
        r"\documentclass[11pt,a4paper]{article}",
        r"\usepackage[margin=2.2cm]{geometry}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage{amssymb}",
        r"\usepackage{fancyhdr}",
        r"\setlength{\parindent}{0pt}",
        r"\pagestyle{fancy}",
        rf"\lhead{{{escape_tex(exam.title)}}}",
        rf"\rhead{{{exam.duration_minutes} min · {exam.total_points} points}}",
        r"\begin{document}",
        rf"\section*{{{escape_tex(exam.title)}}}",
        rf"\textbf{{Duration:}} {exam.duration_minutes} minutes\quad "
        rf"\textbf{{Total:}} {exam.total_points} points",
        r"\vspace{0.5em}",
        r"\hrule",
        r"\vspace{0.8em}",
    ]
    for instruction in exam.instructions:
        lines.append(rf"\textbullet\ {escape_tex(instruction)}\par")
    for index, question in enumerate(exam.questions, start=1):
        lines.extend(
            [
                r"\vspace{1em}",
                rf"\subsection*{{Question {index} \hfill {question.points} points}}",
                escape_tex(question.prompt) + r"\par",
                r"\vspace{0.6em}",
            ]
        )
        if question.kind == "multiple_choice":
            for option in question.options:
                lines.append(rf"$\square$\quad {escape_tex(option)}\par\vspace{{0.35em}}")
        else:
            answer_space = min(8.0, max(2.5, question.points * 0.8))
            lines.append(rf"\vspace{{{answer_space:.1f}cm}}")
            lines.append(r"\hrule")
    lines.extend([r"\end{document}", ""])
    return "\n".join(lines)


def escape_tex(value: str) -> str:
    return "".join(_ESCAPES.get(character, character) for character in value).replace(
        "\n", r"\par "
    )
