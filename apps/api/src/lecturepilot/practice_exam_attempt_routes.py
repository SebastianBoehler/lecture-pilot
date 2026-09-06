from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException

from lecturepilot.api_auth import request_context
from lecturepilot.models import Course, Lecture
from lecturepilot.practice_exam_attempts import (
    PracticeAttempt,
    PracticeAttemptStore,
    PracticeSubmission,
)
from lecturepilot.practice_exam_routes import authorize_practice_exam_access
from lecturepilot.tenancy import TenantContext


def register_practice_exam_attempt_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    seeded_course: Course,
    seeded_lectures: list[Lecture],
) -> None:
    def store(context: TenantContext, course_id: str) -> PracticeAttemptStore:
        authorize_practice_exam_access(
            app,
            context,
            course_id,
            course_tenant_id,
            seeded_course,
            seeded_lectures,
        )
        return PracticeAttemptStore(app.state.practice_exam_store)

    @app.post(
        "/courses/{course_id}/practice-exams/{exam_id}/attempts", response_model=PracticeAttempt
    )
    def submit(
        course_id: str,
        exam_id: str,
        submission: PracticeSubmission,
        context: TenantContext = Depends(request_context),
    ) -> PracticeAttempt:
        attempts = store(context, course_id)
        try:
            return attempts.save(
                user_id=context.user_id, course_id=course_id, exam_id=exam_id, submission=submission
            )
        except FileNotFoundError as exc:
            raise HTTPException(404, "Practice exam not found.") from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get(
        "/courses/{course_id}/practice-exams/{exam_id}/attempts",
        response_model=list[PracticeAttempt],
    )
    def history(
        course_id: str, exam_id: str, context: TenantContext = Depends(request_context)
    ) -> list[PracticeAttempt]:
        attempts = store(context, course_id)
        try:
            return attempts.list(user_id=context.user_id, course_id=course_id, exam_id=exam_id)
        except FileNotFoundError as exc:
            raise HTTPException(404, "Practice exam not found.") from exc

    @app.delete("/courses/{course_id}/practice-exams/{exam_id}/attempts/{attempt_id}")
    def delete(
        course_id: str,
        exam_id: str,
        attempt_id: UUID,
        context: TenantContext = Depends(request_context),
    ) -> dict[str, bool]:
        attempts = store(context, course_id)
        try:
            attempts.delete(
                user_id=context.user_id, course_id=course_id, exam_id=exam_id, attempt_id=attempt_id
            )
        except FileNotFoundError as exc:
            raise HTTPException(404, "Saved attempt not found.") from exc
        return {"deleted": True}
