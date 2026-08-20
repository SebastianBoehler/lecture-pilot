from __future__ import annotations

from pathlib import Path

import fitz

from auth_helpers import student_headers
from lecturepilot.latex_compilation_client import LatexCompilationError
from lecturepilot.practice_exam_pdf import PracticeExamPdfService
from test_practice_exam_api import _client, _generate


def test_pdf_endpoint_is_authenticated_and_user_isolated(tmp_path: Path, monkeypatch) -> None:
    client, _planner = _client(tmp_path)
    client.app.state.practice_exam_pdf_service = PracticeExamPdfService(
        client.app.state.practice_exam_store
    )
    exam_id = _generate(client).json()["id"]
    monkeypatch.setattr(
        "lecturepilot.practice_exam_pdf.compile_latex_document",
        lambda source, output: _write_pdf(output),
    )

    own = client.get(
        f"/courses/martius-ml/practice-exams/{exam_id}/pdf",
        headers=student_headers("student-a"),
    )
    other = client.get(
        f"/courses/martius-ml/practice-exams/{exam_id}/pdf",
        headers=student_headers("student-b"),
    )

    assert own.status_code == 200
    assert own.headers["content-type"] == "application/pdf"
    assert own.content.startswith(b"%PDF")
    assert other.status_code == 404


def test_solution_pdf_is_a_separate_authenticated_document(tmp_path: Path, monkeypatch) -> None:
    client, _planner = _client(tmp_path)
    client.app.state.practice_exam_pdf_service = PracticeExamPdfService(
        client.app.state.practice_exam_store
    )
    exam_id = _generate(client).json()["id"]
    rendered: list[str] = []

    def compile_document(*, source: str, output: Path) -> Path:
        rendered.append(source)
        return _write_pdf(output)

    monkeypatch.setattr("lecturepilot.practice_exam_pdf.compile_latex_document", compile_document)

    own = client.get(
        f"/courses/martius-ml/practice-exams/{exam_id}/solutions/pdf",
        headers=student_headers("student-a"),
    )
    other = client.get(
        f"/courses/martius-ml/practice-exams/{exam_id}/solutions/pdf",
        headers=student_headers("student-b"),
    )

    assert own.status_code == 200
    assert "solution" in own.headers["content-disposition"]
    assert "Correct answer" in rendered[0]
    assert "Full-credit answer" in rendered[0]
    assert (
        client.app.state.practice_exam_store.solution_pdf_path(
            user_id="student-a", course_id="martius-ml", exam_id=exam_id
        ).name
        == "solutions.pdf"
    )
    assert other.status_code == 404


def test_pdf_sources_use_tectonic_native_unicode_fonts(tmp_path: Path, monkeypatch) -> None:
    client, _planner = _client(tmp_path)
    client.app.state.practice_exam_pdf_service = PracticeExamPdfService(
        client.app.state.practice_exam_store
    )
    exam_id = _generate(client).json()["id"]
    rendered: list[str] = []

    def compile_document(*, source: str, output: Path) -> Path:
        rendered.append(source)
        return _write_pdf(output)

    monkeypatch.setattr("lecturepilot.practice_exam_pdf.compile_latex_document", compile_document)

    exam_pdf = client.get(
        f"/courses/martius-ml/practice-exams/{exam_id}/pdf",
        headers=student_headers("student-a"),
    )
    solution_pdf = client.get(
        f"/courses/martius-ml/practice-exams/{exam_id}/solutions/pdf",
        headers=student_headers("student-a"),
    )

    assert exam_pdf.status_code == 200
    assert solution_pdf.status_code == 200
    assert len(rendered) == 2
    assert all(r"\usepackage[T1]{fontenc}" not in source for source in rendered)
    assert all(r"\usepackage[utf8]{inputenc}" not in source for source in rendered)


def test_pdf_retries_transient_compiler_error_before_failing(tmp_path: Path, monkeypatch) -> None:
    client, planner = _client(tmp_path)
    client.app.state.practice_exam_pdf_service = PracticeExamPdfService(
        client.app.state.practice_exam_store
    )
    exam_id = _generate(client).json()["id"]
    calls = 0

    def compile_document(*, source: str, output: Path) -> Path:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise LatexCompilationError("compiler offline", code="compiler_unavailable")
        return _write_pdf(output)

    monkeypatch.setattr("lecturepilot.practice_exam_pdf.compile_latex_document", compile_document)
    first = client.get(
        f"/courses/martius-ml/practice-exams/{exam_id}/pdf",
        headers=student_headers("student-a"),
    )
    assert first.status_code == 200
    assert first.headers["content-type"] == "application/pdf"
    assert first.content.startswith(b"%PDF")
    assert planner.calls == 1
    assert calls == 2


def test_pdf_fallback_without_markup_after_compilation_error(tmp_path: Path, monkeypatch) -> None:
    client, planner = _client(tmp_path)
    client.app.state.practice_exam_pdf_service = PracticeExamPdfService(
        client.app.state.practice_exam_store
    )
    exam_id = _generate(client).json()["id"]
    calls = 0

    def compile_document(*, source: str, output: Path) -> Path:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise LatexCompilationError("latex failed", code="compile_failed")
        return _write_pdf(output)

    monkeypatch.setattr("lecturepilot.practice_exam_pdf.compile_latex_document", compile_document)
    first = client.get(
        f"/courses/martius-ml/practice-exams/{exam_id}/pdf",
        headers=student_headers("student-a"),
    )

    assert first.status_code == 200
    assert first.headers["content-type"] == "application/pdf"
    assert first.content.startswith(b"%PDF")
    assert planner.calls == 1
    assert calls == 2


def test_solution_pdf_retry_failure_maps_compilation_status(tmp_path: Path, monkeypatch) -> None:
    client, planner = _client(tmp_path)
    client.app.state.practice_exam_pdf_service = PracticeExamPdfService(
        client.app.state.practice_exam_store
    )
    exam_id = _generate(client).json()["id"]
    calls = 0

    def compile_document(*, source: str, output: Path) -> Path:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise LatexCompilationError("source modified", code="source_changed")
        return _write_pdf(output)

    monkeypatch.setattr("lecturepilot.practice_exam_pdf.compile_latex_document", compile_document)
    first = client.get(
        f"/courses/martius-ml/practice-exams/{exam_id}/solutions/pdf",
        headers=student_headers("student-a"),
    )
    second = client.get(
        f"/courses/martius-ml/practice-exams/{exam_id}/solutions/pdf",
        headers=student_headers("student-a"),
    )

    assert first.status_code == 502
    assert (
        first.json()["detail"]
        == "Solution PDF source changed during generation. Please retry this lecture from the exam page."
    )
    assert second.status_code == 200
    assert planner.calls == 1
    assert calls == 2


def _write_pdf(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open()
    document.new_page()
    document.save(path)
    document.close()
    return path
