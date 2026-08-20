from __future__ import annotations

from lecturepilot.practice_exam_latex import _render_text, escape_tex
from lecturepilot.practice_exam_models import PracticeExam


def render_practice_exam_solution_tex(
    exam: PracticeExam,
    *,
    include_markup: bool = True,
) -> str:
    lines = [
        r"\documentclass[11pt]{article}",
        r"\usepackage[margin=2.2cm]{geometry}",
        r"\usepackage{amsmath}",
        r"\usepackage{amssymb}",
        r"\usepackage{xcolor}",
        r"\setlength{\parindent}{0pt}",
        r"\begin{document}",
        rf"\section*{{{escape_tex(exam.title)} --- Solutions}}",
        rf"\textbf{{Total: {exam.total_points} points}}",
        r"\vspace{0.8em}",
    ]
    for index, question in enumerate(exam.questions, start=1):
        lines.extend(
            [
                r"\vspace{1em}",
                r"\noindent\begin{minipage}{\textwidth}",
                rf"\subsection*{{Question {index} \hfill {question.points} points}}",
                _render_text(question.prompt, include_markup=include_markup)
                + r"\par\vspace{0.55em}",
            ]
        )
        if question.status == "invalid":
            lines.append(r"\textbf{Invalid question --- do not score.}\par")
        elif question.kind == "multiple_choice":
            answer_index = question.answer_index
            if answer_index is None:
                raise ValueError(f"Question {question.id} has no correct answer.")
            answer_label = chr(ord("A") + answer_index)
            lines.append(
                rf"\textbf{{Correct answer: {answer_label}.}}\quad "
                + _render_text(question.options[answer_index], include_markup=include_markup)
                + r"\par"
            )
        else:
            if not question.reference_answer:
                raise ValueError(f"Question {question.id} has no reference answer.")
            lines.extend(
                [
                    r"\textbf{Full-credit answer}\par",
                    _render_text(question.reference_answer, include_markup=include_markup)
                    + r"\par\vspace{0.45em}",
                    r"\textbf{Full-point criteria}\par",
                ]
            )
            lines.extend(
                rf"\textbullet\ {_render_text(criterion, include_markup=include_markup)}\par"
                for criterion in question.rubric
            )
        lines.append(r"\end{minipage}")
    lines.extend([r"\end{document}", ""])
    return "\n".join(lines)
