from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse

from lecturepilot.api_auth import request_context
from lecturepilot.latex_compilation_client import LatexCompilationError
from lecturepilot.models import Course, Lecture
from lecturepilot.practice_exam_models import (
    PracticeExamSolutionSheet,
    practice_exam_solution_sheet,
)
from lecturepilot.practice_exam_routes import authorize_practice_exam_access
from lecturepilot.tenancy import TenantContext


def register_practice_exam_solution_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    seeded_course: Course,
    seeded_lectures: list[Lecture],
) -> None:
    def authorize(context: TenantContext, course_id: str) -> None:
        authorize_practice_exam_access(
            app,
            context,
            course_id,
            course_tenant_id,
            seeded_course,
            seeded_lectures,
        )

    @app.get(
        "/courses/{course_id}/practice-exams/{exam_id}/solutions",
        response_model=PracticeExamSolutionSheet,
    )
    def solution_sheet(
        course_id: str,
        exam_id: str,
        context: TenantContext = Depends(request_context),
    ) -> PracticeExamSolutionSheet:
        authorize(context, course_id)
        try:
            exam = app.state.practice_exam_store.read(
                user_id=context.user_id, course_id=course_id, exam_id=exam_id
            )
            return practice_exam_solution_sheet(exam)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Practice exam not found.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/courses/{course_id}/practice-exams/{exam_id}/solutions/pdf")
    def solution_pdf(
        course_id: str,
        exam_id: str,
        context: TenantContext = Depends(request_context),
    ) -> FileResponse:
        authorize(context, course_id)
        try:
            path = app.state.practice_exam_pdf_service.render_solutions(
                user_id=context.user_id,
                course_id=course_id,
                exam_id=exam_id,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Practice exam not found.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except LatexCompilationError as exc:
            status = 503 if exc.code == "compiler_unavailable" else 502
            raise HTTPException(
                status_code=status,
                detail="Solution PDF generation is temporarily unavailable. Please retry.",
            ) from exc
        return FileResponse(
            path,
            media_type="application/pdf",
            filename=f"practice-exam-{exam_id[:8]}-solutions.pdf",
        )
