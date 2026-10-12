"""Learner study helpers: course search, last-visit markers and notes export.

All routes are synchronous so FastAPI runs file reads and Markdown parsing in its threadpool.
Lecture access is always derived from the backend session and release policy.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request, Response

from lecturepilot.identity.api_auth import request_context
from lecturepilot.courses.course_access import (
    lecture_views_for_context,
    require_course_id_access,
    require_lecture_id_access,
    resolve_course_lectures,
)
from lecturepilot.canvas.course_canvas_context import InvalidPublishedCanvasContextError
from lecturepilot.authoring.course_canvas_publication import InvalidCanvasPublicationMetadataError
from lecturepilot.courses.course_last_visit import (
    CourseVisitResult,
    CourseVisitStore,
    ReleasedLecture,
    new_lecture_ids,
)
from lecturepilot.learner.learner_notes_export import (
    LearnerNotesExportError,
    export_learner_notes,
    notes_filename,
)
from lecturepilot.learner.lecture_search import (
    LectureSearchResult,
    SearchableLecture,
    normalize_query,
    search_lectures,
)
from lecturepilot.core.models import Course, Lecture, LectureView
from lecturepilot.courses.professor_preview import (
    is_professor_preview_user_id,
    resolve_learner_workspace_access,
)
from lecturepilot.identity.tenancy import TenantContext

_MAX_RAW_QUERY = 400


def register_learner_study_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    seeded_course: Course,
    seeded_lectures: list[Lecture],
) -> None:
    def released_views(context: TenantContext, course_id: str) -> list[LectureView]:
        require_course_id_access(
            app,
            context,
            course_id=course_id,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=seeded_lectures,
        )
        course, lectures = resolve_course_lectures(
            app, course_id=course_id, seeded_course=seeded_course, seeded_lectures=seeded_lectures
        )
        views = lecture_views_for_context(
            app,
            context,
            course,
            lectures,
            course_tenant_id=course_tenant_id,
            invalid_publication_is_unavailable=True,
        )
        return [view for view in views if view.unlocked and view.content_ready]

    def learner_id(request: Request, context: TenantContext, course_id: str) -> str:
        access = resolve_learner_workspace_access(
            request, context, course_id=course_id, course_tenant_id=course_tenant_id
        )
        if is_professor_preview_user_id(access.user_id):
            raise HTTPException(status_code=403, detail="Visits are recorded for learners only.")
        return access.user_id

    @app.get("/courses/{course_id}/search", response_model=LectureSearchResult)
    def search_course(
        course_id: str,
        q: str = "",
        context: TenantContext = Depends(request_context),
    ) -> LectureSearchResult:
        try:
            if len(q) > _MAX_RAW_QUERY:
                raise ValueError
            terms = normalize_query(q)
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail="Search text is too short or too long."
            ) from exc
        store = app.state.canvas_workspace.course_canvas_store
        searchable = []
        for view in released_views(context, course_id):
            try:
                snapshot = store.read_current_published_snapshot(
                    course_id=course_id, lecture_id=view.lecture.id
                )
            except InvalidPublishedCanvasContextError:
                continue
            if snapshot is not None:
                searchable.append(
                    SearchableLecture(
                        id=view.lecture.id, title=view.lecture.title, document=snapshot.document
                    )
                )
        return search_lectures(searchable, terms)

    @app.post("/courses/{course_id}/visits", response_model=CourseVisitResult)
    def record_course_visit(
        course_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> CourseVisitResult:
        user_id = learner_id(request, context, course_id)
        views = released_views(context, course_id)
        state = CourseVisitStore(app.state.canvas_workspace.layout).record_course_visit(
            user_id=user_id, course_id=course_id
        )
        released = [
            ReleasedLecture(id=view.lecture.id, released_at=released_at)
            for view in views
            if (released_at := _released_at(app, course_id, view)) is not None
        ]
        return CourseVisitResult(
            course_id=course_id,
            previous_visit_at=state.previous_visit_at,
            new_lecture_ids=new_lecture_ids(state, released),
        )

    @app.post("/courses/{course_id}/lectures/{lecture_id}/visits", status_code=204)
    def record_lecture_visit(
        course_id: str,
        lecture_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> Response:
        user_id = learner_id(request, context, course_id)
        require_lecture_id_access(
            app,
            context,
            course_id=course_id,
            lecture_id=lecture_id,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=seeded_lectures,
        )
        CourseVisitStore(app.state.canvas_workspace.layout).record_lecture_opened(
            user_id=user_id, course_id=course_id, lecture_id=lecture_id
        )
        return Response(status_code=204)

    @app.get("/courses/{course_id}/lectures/{lecture_id}/notes.md")
    def export_notes(
        course_id: str,
        lecture_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> Response:
        access = resolve_learner_workspace_access(
            request, context, course_id=course_id, course_tenant_id=course_tenant_id
        )
        require_lecture_id_access(
            app,
            context,
            course_id=course_id,
            lecture_id=lecture_id,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=seeded_lectures,
        )
        workspace = app.state.canvas_workspace
        try:
            snapshot = workspace.course_canvas_store.read_current_published_snapshot(
                course_id=course_id, lecture_id=lecture_id
            )
        except InvalidPublishedCanvasContextError as exc:
            raise HTTPException(status_code=404, detail="Lecture not found.") from exc
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Lecture not found.")
        try:
            markdown = export_learner_notes(
                snapshot.document,
                canvas_dir=workspace.layout.user_canvas_dir(access.user_id, course_id, lecture_id),
            )
        except LearnerNotesExportError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if markdown is None:
            raise HTTPException(status_code=404, detail="You have no notes for this lecture yet.")
        return Response(
            content=markdown,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": f'attachment; filename="{notes_filename(lecture_id)}"',
            },
        )


def _released_at(app: FastAPI, course_id: str, view: LectureView) -> datetime | None:
    candidates = [view.effective_publication_at]
    try:
        publication = app.state.canvas_workspace.course_canvas_publication(
            course_id=course_id, lecture_id=view.lecture.id
        )
    except (InvalidCanvasPublicationMetadataError, OSError, ValueError):
        publication = None
    if publication is not None:
        candidates.append(publication.published_at)
    present = [value for value in candidates if value is not None]
    return max(present) if present else None
