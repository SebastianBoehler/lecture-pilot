from __future__ import annotations

from lecturepilot.practice_exam_latex import _render_text, escape_tex
from lecturepilot.practice_exam_models import (
    PracticeExam,
    multiple_select_scoring_instruction,
    question_display_points,
)


def render_practice_exam_solution_tex(
    exam: PracticeExam,
    *,
    include_markup: bool = True,
) -> str:
    de = exam.language == "de"
    solutions, total, points, question_label = (
        ("Lösungen", "Gesamt", "Punkte", "Aufgabe")
        if de
        else ("Solutions", "Total", "points", "Question")
    )
    total_points = sum(question_display_points(q) for q in exam.questions)
    lines = [
        r"\documentclass[11pt]{article}",
        r"\usepackage[margin=2.2cm]{geometry}",
        r"\usepackage{amsmath}",
        r"\usepackage{amssymb}",
        r"\usepackage{xcolor}",
        r"\setlength{\parindent}{0pt}",
        r"\begin{document}",
        rf"\section*{{{escape_tex(exam.title)} --- {solutions}}}",
        rf"\textbf{{{total}: {total_points} {points}}}",
        r"\vspace{0.8em}",
    ]
    if any(question.kind == "multiple_select" for question in exam.questions):
        lines.append(
            _render_text(
                multiple_select_scoring_instruction(exam.language), include_markup=include_markup
            )
            + r"\par"
        )
    for index, question in enumerate(exam.questions, start=1):
        lines.extend(
            [
                r"\vspace{1em}",
                r"\noindent\begin{minipage}{\textwidth}",
                rf"\subsection*{{{question_label} {index} \hfill {question_display_points(question)} {points}}}",
                _render_text(question.prompt, include_markup=include_markup)
                + r"\par\vspace{0.55em}",
            ]
        )
        if question.status == "invalid":
            lines.append(
                r"\textbf{"
                + (
                    "Ungültige Aufgabe --- nicht bewerten."
                    if de
                    else "Invalid question --- do not score."
                )
                + r"}\par"
            )
        elif question.kind in {"multiple_choice", "multiple_select"}:
            indices = (
                question.answer_indices
                if question.kind == "multiple_select"
                else [question.answer_index]
            )
            if not indices or any(i is None for i in indices):
                raise ValueError(f"Question {question.id} has no correct answer.")
            answer_label = ", ".join(chr(ord("A") + i) for i in sorted(indices))
            label = (
                ("Richtige Antworten" if question.kind == "multiple_select" else "Richtige Antwort")
                if de
                else ("Correct answers" if question.kind == "multiple_select" else "Correct answer")
            )
            lines.append(
                rf"\textbf{{{label}: {answer_label}.}}\quad "
                + _render_text(
                    "; ".join(question.options[i] for i in sorted(indices)),
                    include_markup=include_markup,
                )
                + r"\par"
            )
        else:
            if not question.reference_answer:
                raise ValueError(f"Question {question.id} has no reference answer.")
            lines.extend(
                [
                    r"\textbf{" + ("Musterantwort" if de else "Full-credit answer") + r"}\par",
                    _render_text(question.reference_answer, include_markup=include_markup)
                    + r"\par\vspace{0.45em}",
                    r"\textbf{"
                    + ("Bewertungskriterien" if de else "Full-point criteria")
                    + r"}\par",
                ]
            )
            lines.extend(
                rf"\textbullet\ {_render_text(criterion, include_markup=include_markup)}\par"
                for criterion in question.rubric
            )
        lines.append(r"\end{minipage}")
    lines.extend([r"\end{document}", ""])
    return "\n".join(lines)
