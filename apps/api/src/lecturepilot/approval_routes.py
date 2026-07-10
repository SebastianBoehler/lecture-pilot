from __future__ import annotations

from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request

from lecturepilot.account_models import AccountDisabledResponse, ProfessorRequestResponse
from lecturepilot.api_auth import request_context, require_platform_admin
from lecturepilot.approval_repository import ApprovalError, ApprovalRepository
from lecturepilot.tenancy import TenantContext


def register_approval_routes(app: FastAPI) -> None:
    @app.post("/professor-requests", response_model=ProfessorRequestResponse)
    def request_professor(
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> ProfessorRequestResponse:
        principal = getattr(request.state, "session_principal", None)
        if principal is None or principal.account.account_type != "professor":
            raise HTTPException(
                status_code=403,
                detail="Use a professor account to request professor access.",
            )
        try:
            return ApprovalRepository(app.state.database).request_professor(
                user_id=_user_id(context), tenant_id=context.tenant_id
            )
        except ApprovalError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get(
        "/platform/professor-requests",
        response_model=list[ProfessorRequestResponse],
    )
    def pending_professor_requests(
        context: TenantContext = Depends(request_context),
    ) -> list[ProfessorRequestResponse]:
        require_platform_admin(context)
        return ApprovalRepository(app.state.database).pending(tenant_id=context.tenant_id)

    @app.post(
        "/platform/professor-requests/{request_id}/approve",
        response_model=ProfessorRequestResponse,
    )
    def approve_professor_request(
        request_id: UUID,
        context: TenantContext = Depends(request_context),
    ) -> ProfessorRequestResponse:
        return _review(app, request_id, context, "approved")

    @app.post(
        "/platform/professor-requests/{request_id}/reject",
        response_model=ProfessorRequestResponse,
    )
    def reject_professor_request(
        request_id: UUID,
        context: TenantContext = Depends(request_context),
    ) -> ProfessorRequestResponse:
        return _review(app, request_id, context, "rejected")

    @app.post(
        "/platform/users/{user_id}/disable",
        response_model=AccountDisabledResponse,
    )
    def disable_account(
        user_id: UUID,
        context: TenantContext = Depends(request_context),
    ) -> AccountDisabledResponse:
        require_platform_admin(context)
        try:
            disabled = ApprovalRepository(app.state.database).disable_user(
                user_id=user_id,
                actor_id=_user_id(context),
                tenant_id=context.tenant_id,
            )
        except ApprovalError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return AccountDisabledResponse(user_id=user_id, disabled=disabled)


def _review(
    app: FastAPI,
    request_id: UUID,
    context: TenantContext,
    decision: str,
) -> ProfessorRequestResponse:
    require_platform_admin(context)
    try:
        return ApprovalRepository(app.state.database).review(
            request_id=request_id,
            reviewer_id=_user_id(context),
            tenant_id=context.tenant_id,
            decision=decision,
        )
    except ApprovalError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _user_id(context: TenantContext) -> UUID:
    try:
        return UUID(context.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Database account is required.") from exc
