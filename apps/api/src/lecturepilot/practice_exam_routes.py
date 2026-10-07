from __future__ import annotations

from hashlib import sha256
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.responses import FileResponse

from lecturepilot.api_auth import request_context
from lecturepilot.course_access import course_actor_access, require_course_id_access
from lecturepilot.course_canvas_generation_service import validate_generation_request_key
from lecturepilot.latex_compilation_client import LatexCompilationError
from lecturepilot.models import Course, Lecture, TenantRole
from lecturepilot.practice_exam_generation_service import start_exam_generation
from lecturepilot.practice_exam_generation_status import (
    PracticeExamGenerationStatusResponse,
    generation_status_response,
)
from lecturepilot.practice_exam_models import (
    PracticeExamGenerationInput,
    PracticeExamPublic,
    public_practice_exam,
)
from lecturepilot.tenancy import TenantContext


def register_practice_exam_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    seeded_course: Course,
    seeded_lectures: list[Lecture],
) -> None:
    @app.post(
        "/courses/{course_id}/practice-exam-generations",
        response_model=PracticeExamPublic | PracticeExamGenerationStatusResponse,
    )
    async def create_exam(
        course_id: str,
        input_data: PracticeExamGenerationInput,
        response: Response,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
        context: TenantContext = Depends(request_context),
    ) -> PracticeExamPublic | PracticeExamGenerationStatusResponse:
        authorize_practice_exam_access(
            app, context, course_id, course_tenant_id, seeded_course, seeded_lectures
        )
        request_key = _request_key(idempotency_key)
        store = app.state.practice_exam_generation_store
        try:
            job, owns = store.begin(
                user_id=context.user_id,
                course_id=course_id,
                request_key=request_key,
                input_hash=sha256(input_data.model_dump_json().encode()).hexdigest(),
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        response.headers["X-Generation-Id"] = job.generation_id
        response.headers["X-Generation-Status"] = job.status
        if not owns:
            return _replay(app, context, course_id, job)
        result = await start_exam_generation(
            app,
            job=job,
            request_key=request_key,
            context=context,
            course_id=course_id,
            input_data=input_data,
            seeded_course=seeded_course,
            seeded_lectures=seeded_lectures,
        )
        running = isinstance(result, PracticeExamGenerationStatusResponse)
        response.status_code = 202 if running else 200
        response.headers["X-Generation-Status"] = "running" if running else "completed"
        return result

    @app.get(
        "/courses/{course_id}/practice-exam-generations/status",
        response_model=PracticeExamGenerationStatusResponse,
    )
    def generation_status(
        course_id: str,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
        context: TenantContext = Depends(request_context),
    ) -> PracticeExamGenerationStatusResponse:
        authorize_practice_exam_access(
            app, context, course_id, course_tenant_id, seeded_course, seeded_lectures
        )
        job = app.state.practice_exam_generation_store.read(
            user_id=context.user_id,
            course_id=course_id,
            request_key=_request_key(idempotency_key),
        )
        if job is None:
            raise HTTPException(status_code=404, detail="Practice exam generation not found.")
        return generation_status_response(job)

    @app.get("/courses/{course_id}/practice-exams", response_model=list[PracticeExamPublic])
    def list_exams(
        course_id: str, context: TenantContext = Depends(request_context)
    ) -> list[PracticeExamPublic]:
        authorize_practice_exam_access(
            app, context, course_id, course_tenant_id, seeded_course, seeded_lectures
        )
        return [
            public_practice_exam(exam)
            for exam in app.state.practice_exam_store.list(
                user_id=context.user_id, course_id=course_id
            )
        ]

    @app.get("/courses/{course_id}/practice-exams/{exam_id}", response_model=PracticeExamPublic)
    def read_exam(
        course_id: str,
        exam_id: str,
        context: TenantContext = Depends(request_context),
    ) -> PracticeExamPublic:
        authorize_practice_exam_access(
            app, context, course_id, course_tenant_id, seeded_course, seeded_lectures
        )
        return public_practice_exam(_read_exam(app, context.user_id, course_id, exam_id))

    @app.get("/courses/{course_id}/practice-exams/{exam_id}/pdf")
    def exam_pdf(
        course_id: str,
        exam_id: str,
        context: TenantContext = Depends(request_context),
    ) -> FileResponse:
        authorize_practice_exam_access(
            app, context, course_id, course_tenant_id, seeded_course, seeded_lectures
        )
        try:
            path = app.state.practice_exam_pdf_service.render(
                user_id=context.user_id,
                course_id=course_id,
                exam_id=exam_id,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Practice exam not found.") from exc
        except LatexCompilationError as exc:
            status = 503 if exc.code == "compiler_unavailable" else 502
            raise HTTPException(
                status_code=status,
                detail=_pdf_error_detail(exc),
            ) from exc
        return FileResponse(
            path,
            media_type="application/pdf",
            filename=f"practice-exam-{exam_id[:8]}.pdf",
        )

    @app.delete("/courses/{course_id}/practice-exams/{exam_id}")
    def delete_exam(
        course_id: str,
        exam_id: str,
        context: TenantContext = Depends(request_context),
    ) -> dict[str, bool]:
        authorize_practice_exam_access(
            app, context, course_id, course_tenant_id, seeded_course, seeded_lectures
        )
        if not app.state.practice_exam_store.delete(
            user_id=context.user_id, course_id=course_id, exam_id=exam_id
        ):
            raise HTTPException(status_code=404, detail="Practice exam not found.")
        return {"deleted": True}


def authorize_practice_exam_access(
    app, context, course_id, tenant_id, seeded_course, seeded_lectures
) -> None:
    if TenantRole.STUDENT not in context.roles:
        raise HTTPException(status_code=403, detail="Student access is required.")
    if not course_actor_access(app, context, course_id, tenant_id).is_enrolled:
        raise HTTPException(status_code=403, detail="Course enrollment is required.")
    require_course_id_access(
        app,
        context,
        course_id=course_id,
        course_tenant_id=tenant_id,
        seeded_course=seeded_course,
        seeded_lectures=seeded_lectures,
    )


def _request_key(value: str | None) -> str:
    if value is None:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required.")
    try:
        return validate_generation_request_key(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _pdf_error_detail(exc: LatexCompilationError) -> str:
    if exc.code == "compiler_unavailable":
        return "PDF generation is temporarily unavailable. Please retry."
    if exc.code == "source_changed":
        return (
            "Practice exam source changed during generation. Please retry generating the exam PDF."
        )
    if exc.code == "compilation_error":
        return "Practice exam PDF contains invalid source and could not be compiled. Please retry."
    if exc.code == "compiler_rejected":
        return "Practice exam PDF generation was rejected by the compiler. Please retry."
    return "Practice exam PDF generation failed. Please retry."


def _replay(app, context, course_id, job) -> PracticeExamPublic:
    if job.status == "completed" and job.exam_id:
        return public_practice_exam(_read_exam(app, context.user_id, course_id, job.exam_id))
    if job.status == "running":
        raise HTTPException(
            status_code=409,
            detail="Practice exam generation is still running.",
            headers={"Retry-After": "5", "X-Generation-Id": job.generation_id},
        )
    raise HTTPException(
        status_code=409,
        detail="The previous generation failed. Retry with a new Idempotency-Key.",
        headers={"X-Generation-Id": job.generation_id},
    )


def _read_exam(app, user_id: str, course_id: str, exam_id: str):
    try:
        return app.state.practice_exam_store.read(
            user_id=user_id, course_id=course_id, exam_id=exam_id
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Practice exam not found.") from exc
