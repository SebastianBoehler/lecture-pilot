from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request

from lecturepilot.api_auth import require_course_owner, require_learner_workspace_access
from lecturepilot.tenancy import TenantContext


PROFESSOR_PREVIEW_HEADER = "X-LecturePilot-Learner-Preview"
PROFESSOR_PREVIEW_VALUE = "professor"
PROFESSOR_PREVIEW_USER_PREFIX = "professor-preview:"


@dataclass(frozen=True)
class LearnerWorkspaceAccess:
    user_id: str
    actor_user_id: str


def resolve_learner_workspace_access(
    request: Request,
    context: TenantContext,
    *,
    course_id: str,
    course_tenant_id: str,
) -> LearnerWorkspaceAccess:
    mode = request.headers.get(PROFESSOR_PREVIEW_HEADER)
    if mode is None:
        require_learner_workspace_access(
            context,
            learner_user_id=context.user_id,
            course_tenant_id=course_tenant_id,
        )
        return LearnerWorkspaceAccess(
            user_id=context.user_id,
            actor_user_id=context.user_id,
        )
    if mode != PROFESSOR_PREVIEW_VALUE:
        raise HTTPException(status_code=400, detail="Learner preview mode is invalid.")
    require_course_owner(
        request,
        context,
        course_id=course_id,
        course_tenant_id=course_tenant_id,
    )
    return LearnerWorkspaceAccess(
        user_id=professor_preview_user_id(context.user_id, course_id),
        actor_user_id=context.user_id,
    )


def professor_preview_user_id(professor_user_id: str, course_id: str) -> str:
    return f"{PROFESSOR_PREVIEW_USER_PREFIX}{professor_user_id}:{course_id}"


def is_professor_preview_user_id(user_id: str) -> bool:
    return user_id.startswith(PROFESSOR_PREVIEW_USER_PREFIX)
