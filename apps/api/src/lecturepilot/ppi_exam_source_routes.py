from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from lecturepilot.api_auth import request_context
from lecturepilot.course_access import course_actor_access, require_course_id_access
from lecturepilot.models import Course, Lecture, TenantRole
from lecturepilot.ppi_exam_source_archive import PpiArchiveError
from lecturepilot.ppi_exam_source_models import (
    PpiCatalogResponse,
    PpiCredentials,
    PpiExamSourceManifest,
    PpiImportInput,
    PpiImportResult,
)
from lecturepilot.ppi_exam_source_service import (
    PpiAccessError,
    PpiCredentialsError,
    PpiIntegrationUnavailable,
)
from lecturepilot.tenancy import TenantContext


def register_ppi_exam_source_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    seeded_course: Course,
    seeded_lectures: list[Lecture],
) -> None:
    @app.get(
        "/courses/{course_id}/ppi-exam-sources",
        response_model=list[PpiExamSourceManifest],
    )
    def list_sources(
        course_id: str, context: TenantContext = Depends(request_context)
    ) -> list[PpiExamSourceManifest]:
        _authorize(app, context, course_id, course_tenant_id, seeded_course, seeded_lectures)
        return app.state.ppi_exam_source_store.list(user_id=context.user_id, course_id=course_id)

    @app.post(
        "/courses/{course_id}/ppi-exam-sources/catalog",
        response_model=PpiCatalogResponse,
    )
    def catalog(
        course_id: str,
        credentials: PpiCredentials,
        context: TenantContext = Depends(request_context),
    ) -> PpiCatalogResponse:
        _authorize(app, context, course_id, course_tenant_id, seeded_course, seeded_lectures)
        try:
            return app.state.ppi_exam_source_service.catalog(
                user_id=context.user_id,
                course_id=course_id,
                credentials=credentials,
            )
        except PpiCredentialsError as exc:
            raise HTTPException(
                status_code=401,
                detail="PPI rejected the username or PPI-specific password.",
            ) from exc
        except PpiIntegrationUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post(
        "/courses/{course_id}/ppi-exam-sources/imports",
        response_model=PpiImportResult,
    )
    def import_source(
        course_id: str,
        input_data: PpiImportInput,
        context: TenantContext = Depends(request_context),
    ) -> PpiImportResult:
        _authorize(app, context, course_id, course_tenant_id, seeded_course, seeded_lectures)
        try:
            return app.state.ppi_exam_source_service.import_source(
                user_id=context.user_id,
                course_id=course_id,
                input_data=input_data,
            )
        except PpiCredentialsError as exc:
            raise HTTPException(
                status_code=401,
                detail="PPI rejected the username or PPI-specific password.",
            ) from exc
        except PpiAccessError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except PpiArchiveError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except PpiIntegrationUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.delete("/courses/{course_id}/ppi-exam-sources/{source_id}")
    def delete_source(
        course_id: str,
        source_id: str,
        context: TenantContext = Depends(request_context),
    ) -> dict[str, bool]:
        _authorize(app, context, course_id, course_tenant_id, seeded_course, seeded_lectures)
        deleted = app.state.ppi_exam_source_store.delete(
            user_id=context.user_id,
            course_id=course_id,
            source_id=source_id,
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="PPI source not found.")
        return {"deleted": True}


def _authorize(
    app: FastAPI,
    context: TenantContext,
    course_id: str,
    course_tenant_id: str,
    seeded_course: Course,
    lectures: list[Lecture],
) -> None:
    if TenantRole.STUDENT not in context.roles:
        raise HTTPException(status_code=403, detail="Student access is required.")
    actor = course_actor_access(app, context, course_id, course_tenant_id)
    if not actor.is_enrolled:
        raise HTTPException(status_code=403, detail="Course enrollment is required.")
    require_course_id_access(
        app,
        context,
        course_id=course_id,
        course_tenant_id=course_tenant_id,
        seeded_course=seeded_course,
        seeded_lectures=lectures,
    )
