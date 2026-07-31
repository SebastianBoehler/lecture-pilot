from __future__ import annotations

from lecturepilot.practice_exam_latex import escape_tex, render_exam_markup
from lecturepilot.practice_exam_models import PracticeExam


def render_practice_exam_solution_tex(exam: PracticeExam) -> str:
    lines = [
        r"\documentclass[11pt]{article}",
        r"\usepackage[margin=2.2cm]{geometry}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[utf8]{inputenc}",
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
                render_exam_markup(question.prompt) + r"\par\vspace{0.55em}",
            ]
        )
        if question.kind == "multiple_choice":
            answer_index = question.answer_index
            if answer_index is None:
                raise ValueError(f"Question {question.id} has no correct answer.")
            answer_label = chr(ord("A") + answer_index)
            lines.append(
                rf"\textbf{{Correct answer: {answer_label}.}}\quad "
                + render_exam_markup(question.options[answer_index])
                + r"\par"
            )
        else:
            if not question.reference_answer:
                raise ValueError(f"Question {question.id} has no reference answer.")
            lines.extend(
                [
                    r"\textbf{Full-credit answer}\par",
                    render_exam_markup(question.reference_answer) + r"\par\vspace{0.45em}",
                    r"\textbf{Full-point criteria}\par",
                ]
            )
            lines.extend(
                rf"\textbullet\ {render_exam_markup(criterion)}\par"
                for criterion in question.rubric
            )
        lines.append(r"\end{minipage}")
    lines.extend([r"\end{document}", ""])
    return "\n".join(lines)
