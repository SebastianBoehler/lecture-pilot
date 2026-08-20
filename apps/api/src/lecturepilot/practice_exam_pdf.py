from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import time
from typing import Any

from lecturepilot.latex_compilation_client import LatexCompilationError, compile_latex_document
from lecturepilot.practice_exam_latex import render_practice_exam_tex
from lecturepilot.practice_exam_models import public_practice_exam
from lecturepilot.practice_exam_solution_latex import render_practice_exam_solution_tex
from lecturepilot.practice_exam_store import PracticeExamStore


_COMPILER_RETRIES = [0.20, 0.40]


def _should_retry_compilation(exc: LatexCompilationError) -> bool:
    return exc.code in {"compiler_unavailable", "compiler_busy", "compile_timeout"}


def _should_fallback_to_plain_text(exc: LatexCompilationError) -> bool:
    return exc.code in {"compilation_error", "compile_failed", "compiler_rejected"}


class PracticeExamPdfService:
    def __init__(self, store: PracticeExamStore) -> None:
        self.store = store

    def render(self, *, user_id: str, course_id: str, exam_id: str) -> Path:
        exam = self.store.read(user_id=user_id, course_id=course_id, exam_id=exam_id)
        return self._render_with_fallback(
            exam=public_practice_exam(exam),
            output=self.store.pdf_path(user_id=user_id, course_id=course_id, exam_id=exam_id),
            render=render_practice_exam_tex,
        )

    def render_solutions(self, *, user_id: str, course_id: str, exam_id: str) -> Path:
        exam = self.store.read(user_id=user_id, course_id=course_id, exam_id=exam_id)
        return self._render_with_fallback(
            exam=exam,
            output=self.store.solution_pdf_path(
                user_id=user_id, course_id=course_id, exam_id=exam_id
            ),
            render=render_practice_exam_solution_tex,
        )

    def _render_with_fallback(
        self,
        *,
        exam,
        output: Path,
        render: Callable[[Any], str],
    ) -> Path:
        fallback_mode = False
        attempts = 0
        while True:
            attempts += 1
            try:
                source = render(exam, include_markup=not fallback_mode)
                return compile_latex_document(source=source, output=output)
            except LatexCompilationError as exc:
                if _should_retry_compilation(exc) and attempts <= len(_COMPILER_RETRIES):
                    time.sleep(_COMPILER_RETRIES[attempts - 1])
                    continue
                if not fallback_mode and _should_fallback_to_plain_text(exc):
                    fallback_mode = True
                    continue
                raise
