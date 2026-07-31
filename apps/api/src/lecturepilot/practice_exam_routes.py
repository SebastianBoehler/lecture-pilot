from __future__ import annotations

from hashlib import sha256
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from lecturepilot.api_auth import request_context
from lecturepilot.course_access import course_actor_access, require_course_id_access
from lecturepilot.course_canvas_generation_service import validate_generation_request_key
from lecturepilot.metadata_events import emit_metadata_event
from lecturepilot.latex_compilation_client import LatexCompilationError
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import Course, Lecture, TenantRole
from lecturepilot.practice_exam_generation import generate_practice_exam
from lecturepilot.practice_exam_generation_jobs import PracticeExamGenerationJob
from lecturepilot.practice_exam_models import (
    PracticeExamGenerationInput,
    PracticeExamPublic,
    public_practice_exam,
)
from lecturepilot.practice_exam_planner import PracticeExamPlanningError
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.tenancy import TenantContext


class PracticeExamGenerationStatusResponse(BaseModel):
    generation_id: str
    status: str
    attempt: int
    error_code: str | None = None
    exam_id: str | None = None


def register_practice_exam_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    seeded_course: Course,
    seeded_lectures: list[Lecture],
) -> None:
    @app.post(
        "/courses/{course_id}/practice-exam-generations",
        response_model=PracticeExamPublic,
    )
    async def create_exam(
        course_id: str,
        input_data: PracticeExamGenerationInput,
        response: Response,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
        context: TenantContext = Depends(request_context),
    ) -> PracticeExamPublic:
        _authorize(app, context, course_id, course_tenant_id, seeded_course, seeded_lectures)
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
        try:
            exam = await generate_practice_exam(
                app,
                context=context,
                course_id=course_id,
                input_data=input_data,
                seeded_course=seeded_course,
                seeded_lectures=seeded_lectures,
            )
            app.state.practice_exam_store.write(
                user_id=context.user_id, course_id=course_id, exam=exam
            )
            job = store.complete(
                job,
                user_id=context.user_id,
                request_key=request_key,
                exam_id=exam.id,
            )
            response.headers["X-Generation-Status"] = job.status
            emit_metadata_event(
                "practice_exam.generated",
                question_count=len(exam.questions),
                ppi_source_count=len(input_data.ppi_source_ids),
                status="completed",
            )
            return public_practice_exam(exam)
        except HTTPException:
            store.fail(
                job,
                user_id=context.user_id,
                request_key=request_key,
                error_code="source_error",
            )
            raise
        except ProviderConfigurationError as exc:
            _fail(store, job, context.user_id, request_key, "provider_configuration_error")
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ModelExecutionError as exc:
            _fail(store, job, context.user_id, request_key, "model_execution_error")
            raise HTTPException(
                status_code=502, detail="Practice exam generation failed. Please retry."
            ) from exc
        except PracticeExamPlanningError as exc:
            _fail(store, job, context.user_id, request_key, "invalid_model_output")
            raise HTTPException(
                status_code=502, detail="Practice exam generation failed validation. Please retry."
            ) from exc
        except Exception:
            _fail(store, job, context.user_id, request_key, "unexpected_error")
            raise

    @app.get(
        "/courses/{course_id}/practice-exam-generations/status",
        response_model=PracticeExamGenerationStatusResponse,
    )
    def generation_status(
        course_id: str,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
        context: TenantContext = Depends(request_context),
    ) -> PracticeExamGenerationStatusResponse:
        _authorize(app, context, course_id, course_tenant_id, seeded_course, seeded_lectures)
        job = app.state.practice_exam_generation_store.read(
            user_id=context.user_id,
            course_id=course_id,
            request_key=_request_key(idempotency_key),
        )
        if job is None:
            raise HTTPException(status_code=404, detail="Practice exam generation not found.")
        return _status(job)

    @app.get("/courses/{course_id}/practice-exams", response_model=list[PracticeExamPublic])
    def list_exams(
        course_id: str, context: TenantContext = Depends(request_context)
    ) -> list[PracticeExamPublic]:
        _authorize(app, context, course_id, course_tenant_id, seeded_course, seeded_lectures)
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
        _authorize(app, context, course_id, course_tenant_id, seeded_course, seeded_lectures)
        return public_practice_exam(_read_exam(app, context.user_id, course_id, exam_id))

    @app.get("/courses/{course_id}/practice-exams/{exam_id}/pdf")
    def exam_pdf(
        course_id: str,
        exam_id: str,
        context: TenantContext = Depends(request_context),
    ) -> FileResponse:
        _authorize(app, context, course_id, course_tenant_id, seeded_course, seeded_lectures)
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
                detail="PDF generation is temporarily unavailable. Please retry.",
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
        _authorize(app, context, course_id, course_tenant_id, seeded_course, seeded_lectures)
        if not app.state.practice_exam_store.delete(
            user_id=context.user_id, course_id=course_id, exam_id=exam_id
        ):
            raise HTTPException(status_code=404, detail="Practice exam not found.")
        return {"deleted": True}


def _authorize(app, context, course_id, tenant_id, seeded_course, seeded_lectures) -> None:
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


def _status(job: PracticeExamGenerationJob) -> PracticeExamGenerationStatusResponse:
    return PracticeExamGenerationStatusResponse(
        generation_id=job.generation_id,
        status=job.status,
        attempt=job.attempt,
        error_code=job.error_code,
        exam_id=job.exam_id,
    )


def _fail(store, job, user_id: str, request_key: str, error_code: str) -> None:
    store.fail(job, user_id=user_id, request_key=request_key, error_code=error_code)
