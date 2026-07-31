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


def test_pdf_retry_does_not_regenerate_exam(tmp_path: Path, monkeypatch) -> None:
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
    retry = client.get(
        f"/courses/martius-ml/practice-exams/{exam_id}/pdf",
        headers=student_headers("student-a"),
    )

    assert first.status_code == 503
    assert first.json()["detail"] == "PDF generation is temporarily unavailable. Please retry."
    assert retry.status_code == 200
    assert planner.calls == 1
    assert calls == 2


def _write_pdf(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open()
    document.new_page()
    document.save(path)
    document.close()
    return path
