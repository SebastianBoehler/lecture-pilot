from datetime import date
from pathlib import Path

import pytest

from lecturepilot.courses.lecture_schedule import propose_lecture_schedule
from lecturepilot.courses.lecture_schedule_evidence import build_schedule_evidence
from lecturepilot.courses.lecture_title import document_title
from lecturepilot.sources.source_bundle import SourceBundleFile


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (r"\title{Lecture 03: Regularization}\section{Overfitting}", "Regularization"),
        (r"\title[Short]{Vorlesung 4 -- Bayes\\ Klassifikation}", "Bayes Klassifikation"),
        (r"\title{\textbf{Lecture 5}: Kernels \& SVMs}", "Kernels & SVMs"),
        # A bare number names no topic: metadata, then the first real heading decide.
        (r"\title{Lecture 03}\hypersetup{pdftitle={Lecture 3: Ridge}}", "Ridge"),
        (r"\title{Lecture 03}\section{Course thread}\section{Overfitting}", "Overfitting"),
        (r"\begin{frame}{Plan for today}\end{frame}\frametitle{Margins}", "Margins"),
        (r"No structure at all", None),
    ],
)
def test_latex_title_precedes_metadata_and_headings(text: str, expected: str | None) -> None:
    assert document_title(text, markdown=False) == expected


def test_markdown_front_matter_title_precedes_the_first_heading() -> None:
    text = "---\ntitle: 'Lecture 07: Attention'\n---\n# Recap\n"
    assert document_title(text, markdown=True) == "Attention"
    assert document_title("# Lecture 02: Gradient Descent\n", markdown=True) == "Gradient Descent"


def test_new_lecture_proposal_uses_the_latex_title(tmp_path: Path) -> None:
    source = tmp_path / "Lecture03.tex"
    source.write_text(
        "\\documentclass{beamer}\n\\title{Lecture 03: Regularization}\n"
        "\\begin{document}\\section{Overfitting}\\end{document}\n",
        encoding="utf-8",
    )
    file = SourceBundleFile(path="Lecture03.tex", kind="latex", size_bytes=1)
    proposal = propose_lecture_schedule(
        course_id="course", files=[file], roots=[tmp_path], first_lecture_date=date(2026, 10, 1)
    )
    evidence = build_schedule_evidence("course", [file], [tmp_path], None, None)

    assert proposal.lectures[0].title == "Regularization"
    assert "title cue: Regularization" in evidence
