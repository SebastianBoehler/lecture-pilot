"""Course links professors share in lectures; joining counts as course enrollment.

The secret lives in the private course root so professors can show the same link and QR
code again; rotating replaces it and disabling removes it. A join writes an `invite`
enrollment that university sync never deactivates.
"""

from datetime import UTC, datetime
import hmac
import json
import secrets
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from lecturepilot.identity.api_auth import request_context, require_course_manager
from lecturepilot.courses.course_schedule_store import read_course_workspace
from lecturepilot.core.db_models import AuditEventRecord, CourseEnrollmentRecord, CourseRecord
from lecturepilot.core.durable_files import atomic_write_json
from lecturepilot.courses.lecture_access_models import CourseAccessPolicy
from lecturepilot.identity.tenancy import TenantContext

INVITE_SOURCE = "invite"


class CourseInvite(BaseModel):
    path: str


class CoursePreview(BaseModel):
    title: str
    term: str
    lecture_count: int
    canvas_language: str


class CourseJoinResult(BaseModel):
    course_id: str
    joined: bool


def register_course_invite_routes(app: FastAPI, *, course_tenant_id: str) -> None:
    def invite_path(course_id: str):
        return app.state.canvas_workspace.layout.course_root(course_id) / "invite.json"

    def workspace(course_id: str):
        course_root = app.state.canvas_workspace.course_media_root(course_id)
        found = read_course_workspace(course_root, course_id)
        if found is None:
            raise HTTPException(status_code=404, detail="Course was not found.")
        return found

    def require_valid_code(course_id: str, code: str):
        found = workspace(course_id)
        path = invite_path(course_id)
        saved = json.loads(path.read_text()) if path.exists() else {}
        secret = saved.get("secret", "")
        shareable = found.course.access_policy is not CourseAccessPolicy.INSTRUCTORS_ONLY
        if not (secret and shareable and hmac.compare_digest(secret, code)):
            raise HTTPException(status_code=404, detail="This course link is not valid.")
        return found

    def link(course_id: str, secret: str) -> CourseInvite:
        return CourseInvite(path=f"/join/{course_id}/{secret}")

    @app.get("/admin/courses/{course_id}/invite", response_model=CourseInvite | None)
    def current_invite(
        course_id: str, request: Request, context: TenantContext = Depends(request_context)
    ):
        require_course_manager(
            context, course_tenant_id=course_tenant_id, request=request, course_id=course_id
        )
        path = invite_path(course_id)
        secret = json.loads(path.read_text()).get("secret") if path.exists() else None
        return link(course_id, secret) if secret else None

    @app.post("/admin/courses/{course_id}/invite", response_model=CourseInvite)
    def rotate_invite(
        course_id: str, request: Request, context: TenantContext = Depends(request_context)
    ):
        require_course_manager(
            context, course_tenant_id=course_tenant_id, request=request, course_id=course_id
        )
        if workspace(course_id).course.access_policy is CourseAccessPolicy.INSTRUCTORS_ONLY:
            raise HTTPException(status_code=409, detail="Instructor-only courses cannot be shared.")
        secret = secrets.token_urlsafe(16)
        atomic_write_json(
            invite_path(course_id),
            {"secret": secret, "created_at": datetime.now(UTC).isoformat()},
        )
        return link(course_id, secret)

    @app.delete("/admin/courses/{course_id}/invite", status_code=204)
    def disable_invite(
        course_id: str, request: Request, context: TenantContext = Depends(request_context)
    ):
        require_course_manager(
            context, course_tenant_id=course_tenant_id, request=request, course_id=course_id
        )
        invite_path(course_id).unlink(missing_ok=True)

    @app.get("/join/{course_id}/{code}", response_model=CoursePreview)
    def preview(course_id: str, code: str):
        found = require_valid_code(course_id, code)
        return CoursePreview(
            title=found.course.title,
            term=found.course.term,
            lecture_count=len(found.lectures),
            canvas_language=found.course.canvas_language,
        )

    @app.post("/join/{course_id}/{code}", response_model=CourseJoinResult)
    def join(course_id: str, code: str, context: TenantContext = Depends(request_context)):
        require_valid_code(course_id, code)
        if context.auth_mode != "session":
            raise HTTPException(
                status_code=409, detail="Joining a course requires a university login."
            )
        try:
            course_uuid, user_uuid = UUID(course_id), UUID(context.user_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="This course link is not valid.") from exc
        with app.state.database.session() as session:
            course = session.get(CourseRecord, course_uuid)
            if course is None or course.tenant_id != course_tenant_id:
                raise HTTPException(status_code=404, detail="This course link is not valid.")
            enrollment = session.scalar(
                select(CourseEnrollmentRecord).where(
                    CourseEnrollmentRecord.course_id == course_uuid,
                    CourseEnrollmentRecord.user_id == user_uuid,
                    CourseEnrollmentRecord.source == INVITE_SOURCE,
                )
            )
            if enrollment is None:
                session.add(
                    CourseEnrollmentRecord(
                        course_id=course_uuid,
                        user_id=user_uuid,
                        source=INVITE_SOURCE,
                        external_course_id=INVITE_SOURCE,
                        status="active",
                    )
                )
            else:
                enrollment.status = "active"
            session.add(
                AuditEventRecord(
                    tenant_id=course_tenant_id,
                    actor_user_id=user_uuid,
                    event_type="course.invite_joined",
                    target_type="course",
                    target_id=course_id,
                    details={},
                )
            )
        return CourseJoinResult(course_id=course_id, joined=True)
