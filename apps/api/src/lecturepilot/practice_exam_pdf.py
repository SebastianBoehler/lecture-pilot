from __future__ import annotations

from pathlib import Path

from lecturepilot.latex_compilation_client import compile_latex_document
from lecturepilot.practice_exam_latex import render_practice_exam_tex
from lecturepilot.practice_exam_models import public_practice_exam
from lecturepilot.practice_exam_solution_latex import render_practice_exam_solution_tex
from lecturepilot.practice_exam_store import PracticeExamStore


class PracticeExamPdfService:
    def __init__(self, store: PracticeExamStore) -> None:
        self.store = store

    def render(self, *, user_id: str, course_id: str, exam_id: str) -> Path:
        exam = self.store.read(user_id=user_id, course_id=course_id, exam_id=exam_id)
        source = render_practice_exam_tex(public_practice_exam(exam))
        return compile_latex_document(
            source=source,
            output=self.store.pdf_path(user_id=user_id, course_id=course_id, exam_id=exam_id),
        )

    def render_solutions(self, *, user_id: str, course_id: str, exam_id: str) -> Path:
        exam = self.store.read(user_id=user_id, course_id=course_id, exam_id=exam_id)
        return compile_latex_document(
            source=render_practice_exam_solution_tex(exam),
            output=self.store.solution_pdf_path(
                user_id=user_id, course_id=course_id, exam_id=exam_id
            ),
        )
