from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import fitz
import pytest

from lecturepilot.latex_compilation_client import (
    LatexCompilationError,
    compile_latex_document,
)
from lecturepilot.practice_exam_latex import render_practice_exam_tex
from lecturepilot.practice_exam_models import (
    PracticeExamPublic,
    PracticeExamPublicQuestion,
)


def test_tex_renderer_escapes_untrusted_text_and_omits_private_authoring_data() -> None:
    exam = _public_exam(prompt=r"Use \ { } % $ & _ # ^ ~ safely")

    tex = render_practice_exam_tex(exam)

    for escaped in (
        r"\textbackslash{}",
        r"\{",
        r"\}",
        r"\%",
        r"\$",
        r"\&",
        r"\_",
        r"\#",
        r"\textasciicircum{}",
        r"\textasciitilde{}",
    ):
        assert escaped in tex
    assert tex.index("Question 1") < tex.index("Question 2")
    assert r"$\square$" in tex
    assert r"\vspace" in tex
    assert tex.count(r"\begin{minipage}{\textwidth}") == len(exam.questions)
    assert tex.count(r"\end{minipage}") == len(exam.questions)
    assert r"\fancyhf{}" in tex
    assert r"\setlength{\headheight}{14pt}" in tex
    assert "answer_index" not in tex
    assert "rubric" not in tex
    assert "source_ids" not in tex


def test_tex_renderer_supports_safe_markdown_and_latex_in_exam_content() -> None:
    exam = _public_exam(
        prompt=r"Compute $P(w_i \mid w_{i-1}) = \frac{c(w_{i-1},w_i)}{c(w_{i-1})}$ for `new`."
    )
    exam.instructions = ["Use **clear reasoning**."]
    exam.questions[0].options = ["*Maximum likelihood*", "Uniform probability"]
    exam.questions[1].prompt = r"Interpret $$\begin{bmatrix}1 & 0 \\ 0 & 1\end{bmatrix}$$."

    tex = render_practice_exam_tex(exam)

    assert r"\textbf{clear reasoning}" in tex
    assert r"\texttt{new}" in tex
    assert r"\emph{Maximum likelihood}" in tex
    assert r"$P(w_i \mid w_{i-1}) = \frac{c(w_{i-1},w_i)}{c(w_{i-1})}$" in tex
    assert r"\usepackage{amsmath}" in tex
    assert r"\[\begin{bmatrix}1 & 0 \\ 0 & 1\end{bmatrix}\]" in tex


def test_tex_renderer_escapes_disallowed_commands_inside_math_delimiters() -> None:
    exam = _public_exam(prompt=r"Do not execute $x \input{/etc/passwd}$ here.")

    tex = render_practice_exam_tex(exam)

    assert r"$x \input{/etc/passwd}$" not in tex
    assert r"\textbackslash{}input\{/etc/passwd\}" in tex


def test_tex_renderer_escapes_mismatched_math_environments() -> None:
    exam = _public_exam(prompt=r"Do not compile $$\begin{matrix}x\end{pmatrix}$$ here.")

    tex = render_practice_exam_tex(exam)

    assert r"\[\begin{matrix}x\end{pmatrix}\]" not in tex
    assert r"\textbackslash{}begin\{matrix\}" in tex


def test_tex_renderer_preserves_invalid_question_number_without_answer_space() -> None:
    exam = _public_exam()
    exam.questions[12] = PracticeExamPublicQuestion(
        id="q-13",
        kind="open_ended",
        status="invalid",
        prompt="INVALID QUESTION — DO NOT SCORE.",
        points=0,
        options=[],
    )
    exam.total_points -= 2

    tex = render_practice_exam_tex(exam)
    question = tex[tex.index("Question 13") : tex.index("Question 14")]

    assert "INVALID QUESTION" in question
    assert r"\hrule" not in question


def test_generic_document_compiler_uses_content_fingerprint_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def compile_request(archive, size: int, main_path: str) -> bytes:
        nonlocal calls
        calls += 1
        assert main_path == "document.tex"
        return _pdf_bytes(f"compiled-{calls}")

    monkeypatch.setattr(
        "lecturepilot.latex_compilation_client._request_compilation", compile_request
    )
    output = tmp_path / "exam.pdf"

    first = compile_latex_document(source="first", output=output)
    cached = compile_latex_document(source="first", output=output)
    changed = compile_latex_document(source="second", output=output)

    assert first == cached == changed == output
    assert calls == 2


def test_generic_document_compiler_rejects_invalid_pdf_without_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "lecturepilot.latex_compilation_client._request_compilation",
        lambda archive, size, main_path: b"not-pdf",
    )

    with pytest.raises(LatexCompilationError, match="valid PDF"):
        compile_latex_document(source="exam", output=tmp_path / "exam.pdf")

    assert not (tmp_path / "exam.pdf").exists()


def test_generic_document_compiler_reports_unavailable_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LECTUREPILOT_LATEX_COMPILER_URL", raising=False)

    with pytest.raises(LatexCompilationError, match="not configured"):
        compile_latex_document(source="exam", output=tmp_path / "exam.pdf")


def _public_exam(*, prompt: str = "Choose the correct claim.") -> PracticeExamPublic:
    questions = []
    for index in range(1, 21):
        questions.append(
            PracticeExamPublicQuestion(
                id=f"q-{index:02d}",
                kind="multiple_choice" if index % 2 else "open_ended",
                prompt=prompt if index == 1 else f"Question {index}",
                points=2,
                options=["Option A", "Option B"] if index % 2 else [],
            )
        )
    return PracticeExamPublic(
        id="a" * 32,
        course_id="martius-ml",
        title="ML & Safety",
        language="en",
        instructions=["Answer every question."],
        duration_minutes=90,
        created_at=datetime.now(UTC),
        total_points=40,
        questions=questions,
    )


def _pdf_bytes(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    payload = document.tobytes()
    document.close()
    return payload
