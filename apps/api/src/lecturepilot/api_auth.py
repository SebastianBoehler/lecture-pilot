from __future__ import annotations

from fastapi import Header, HTTPException

from lecturepilot.models import TenantRole
from lecturepilot.session_auth import (
    SessionAuthError,
    SessionAuthSettings,
    context_from_bearer_token,
)
from lecturepilot.tenancy import (
    TenantAccessError,
    TenantContext,
    assert_can_manage_course,
    assert_can_view_progress,
)


def request_context(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_user_role: TenantRole | None = Header(default=None, alias="X-User-Role"),
) -> TenantContext:
    if authorization:
        try:
            return context_from_bearer_token(authorization)
        except SessionAuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    try:
        settings = SessionAuthSettings.from_env()
    except SessionAuthError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not settings.allow_dev_headers:
        raise HTTPException(status_code=401, detail="Bearer session token is required.")

    if not x_user_id or not x_user_id.strip():
        raise HTTPException(status_code=401, detail="Authentication is required.")
    if not x_tenant_id or not x_tenant_id.strip() or x_user_role is None:
        raise HTTPException(status_code=401, detail="Authentication headers are required.")
    return TenantContext(
        tenant_id=x_tenant_id.strip(),
        user_id=x_user_id.strip(),
        roles=frozenset({x_user_role}),
    )


def require_course_manager(context: TenantContext, *, course_tenant_id: str) -> None:
    try:
        assert_can_manage_course(context, course_tenant_id=course_tenant_id)
    except TenantAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def require_same_tenant(context: TenantContext, *, course_tenant_id: str) -> None:
    if context.tenant_id != course_tenant_id:
        raise HTTPException(status_code=403, detail="Resource does not belong to the active tenant.")


def require_learner_workspace_access(
    context: TenantContext,
    *,
    learner_user_id: str,
    course_tenant_id: str,
) -> None:
    try:
        assert_can_view_progress(
            context,
            learner_user_id=learner_user_id,
            progress_tenant_id=course_tenant_id,
        )
    except TenantAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
