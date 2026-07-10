from __future__ import annotations

from uuid import UUID

from fastapi import Header, HTTPException, Request

from lecturepilot.course_repository import CourseRepository
from lecturepilot.models import TenantRole
from lecturepilot.session_auth import (
    SESSION_COOKIE_NAME,
    SessionAuthError,
    SessionAuthSettings,
    bearer_token,
)
from lecturepilot.session_store import SessionPrincipal, SessionStoreError
from lecturepilot.tenancy import TenantContext


def request_context(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_course_ids: str | None = Header(default=None, alias="X-Course-Ids"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_user_role: TenantRole | None = Header(default=None, alias="X-User-Role"),
) -> TenantContext:
    try:
        settings = SessionAuthSettings.from_env()
    except SessionAuthError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if settings.allow_dev_headers and x_user_id and x_user_id.strip():
        return _context_from_dev_headers(
            x_course_ids=x_course_ids,
            x_tenant_id=x_tenant_id,
            x_user_id=x_user_id,
            x_user_role=x_user_role,
        )
    try:
        header_token = bearer_token(authorization)
    except SessionAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    token = header_token or request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Session cookie or bearer token is required.")
    try:
        principal = request.app.state.session_store.authenticate(token)
    except SessionStoreError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    request.state.session_principal = principal
    request.state.session_token = token
    request.state.auth_transport = "bearer" if header_token else "cookie"
    return _context_from_principal(principal)


def require_platform_admin(context: TenantContext) -> None:
    if TenantRole.TENANT_ADMIN not in context.roles:
        raise HTTPException(status_code=403, detail="Platform administrator access is required.")


def require_approved_professor(context: TenantContext) -> None:
    if TenantRole.PROFESSOR not in context.roles:
        raise HTTPException(status_code=403, detail="Approved professor access is required.")


def require_course_owner(
    request: Request,
    context: TenantContext,
    *,
    course_id: str,
    course_tenant_id: str,
) -> None:
    require_same_tenant(context, course_tenant_id=course_tenant_id)
    if context.auth_mode == "dev":
        require_approved_professor(context)
        return
    repository = CourseRepository(request.app.state.database)
    if not repository.is_owner(
        user_id=_user_uuid(context),
        tenant_id=course_tenant_id,
        course_id=course_id,
    ):
        raise HTTPException(status_code=403, detail="Course ownership is required.")


def require_course_manager(
    context: TenantContext,
    *,
    course_tenant_id: str,
    request: Request | None = None,
    course_id: str | None = None,
) -> None:
    if context.auth_mode == "dev":
        require_same_tenant(context, course_tenant_id=course_tenant_id)
        require_approved_professor(context)
        return
    if request is None or course_id is None:
        raise HTTPException(status_code=403, detail="Course ownership is required.")
    require_course_owner(
        request,
        context,
        course_id=course_id,
        course_tenant_id=course_tenant_id,
    )


def require_same_tenant(context: TenantContext, *, course_tenant_id: str) -> None:
    if context.tenant_id != course_tenant_id:
        raise HTTPException(
            status_code=403, detail="Resource does not belong to the active tenant."
        )


def require_learner_workspace_access(
    context: TenantContext,
    *,
    learner_user_id: str,
    course_tenant_id: str,
) -> None:
    require_same_tenant(context, course_tenant_id=course_tenant_id)
    if TenantRole.STUDENT not in context.roles:
        raise HTTPException(status_code=403, detail="Student workspace access is required.")
    if context.user_id != learner_user_id:
        raise HTTPException(
            status_code=403,
            detail="Learner workspace belongs only to the active learner.",
        )


def _context_from_principal(principal: SessionPrincipal) -> TenantContext:
    account = principal.account
    return TenantContext(
        tenant_id=account.tenant_id,
        user_id=str(account.user_id),
        roles=account.roles,
        course_ids=account.course_ids,
        auth_mode="session",
    )


def _context_from_dev_headers(
    *,
    x_course_ids: str | None,
    x_user_id: str | None,
    x_tenant_id: str | None,
    x_user_role: TenantRole | None,
) -> TenantContext:
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(status_code=401, detail="Authentication is required.")
    if not x_tenant_id or not x_tenant_id.strip() or x_user_role is None:
        raise HTTPException(status_code=401, detail="Authentication headers are required.")
    return TenantContext(
        tenant_id=x_tenant_id.strip(),
        user_id=x_user_id.strip(),
        roles=frozenset({x_user_role}),
        course_ids=_parse_course_ids(x_course_ids),
        auth_mode="dev",
    )


def _parse_course_ids(header: str | None) -> frozenset[str]:
    if not header:
        return frozenset()
    course_ids = [course_id.strip() for course_id in header.split(",")]
    return frozenset(course_id for course_id in course_ids if course_id)


def _user_uuid(context: TenantContext) -> UUID:
    try:
        return UUID(context.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Session user identity is invalid.") from exc
