from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from lecturepilot.api_auth import request_context, require_learner_workspace_access
from lecturepilot.canvas_workspace import CanvasWorkspaceError
from lecturepilot.course_schedule_store import read_course_workspace
from lecturepilot.exam_readiness import ExamReadinessCheck, build_exam_readiness_check
from lecturepilot.models import Lecture
from lecturepilot.tenancy import TenantContext


def register_exam_readiness_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    lectures: list[Lecture],
) -> None:
    @app.get("/courses/{course_id}/exam-readiness", response_model=ExamReadinessCheck)
    def exam_readiness_check(
        course_id: str,
        context: TenantContext = Depends(request_context),
    ) -> ExamReadinessCheck:
        require_learner_workspace_access(
            context,
            learner_user_id=context.user_id,
            course_tenant_id=course_tenant_id,
        )
        course_lectures = _course_lectures(app, course_id, lectures)
        documents = []
        for lecture in course_lectures:
            if not app.state.canvas_workspace.has_published_course_canvas(
                course_id=course_id,
                lecture_id=lecture.id,
            ):
                continue
            try:
                document = app.state.canvas_workspace.course_canvas_store.read(
                    course_id=course_id,
                    lecture_id=lecture.id,
                    workspace_path=f"exam-readiness/{lecture.id}/index.md",
                )
            except CanvasWorkspaceError:
                continue
            if document is not None:
                documents.append(document)
        if not documents:
            raise HTTPException(
                status_code=404,
                detail="Publish at least one lecture canvas before running the exam readiness check.",
            )
        check = build_exam_readiness_check(
            course_id=course_id,
            documents=documents,
            lectures=course_lectures,
        )
        if not check.questions:
            raise HTTPException(
                status_code=422,
                detail="Published canvases do not contain enough quiz or section content for an exam readiness check.",
            )
        return check


def _course_lectures(app: FastAPI, course_id: str, seeded_lectures: list[Lecture]) -> list[Lecture]:
    workspace = read_course_workspace(app.state.canvas_workspace.course_media_root(course_id), course_id)
    if workspace:
        return workspace.lectures
    matching = [lecture for lecture in seeded_lectures if lecture.course_id == course_id]
    if matching:
        return matching
    raise HTTPException(status_code=404, detail="Course not found.")
