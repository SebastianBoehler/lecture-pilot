from __future__ import annotations

from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException

from lecturepilot.account_admin_repository import AccountAdminError, AccountAdminRepository
from lecturepilot.account_models import AccountDisabledResponse
from lecturepilot.api_auth import request_context, require_platform_admin
from lecturepilot.tenancy import TenantContext


def register_account_admin_routes(app: FastAPI) -> None:
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
            disabled = AccountAdminRepository(app.state.database).disable_user(
                user_id=user_id,
                actor_id=_user_id(context),
                tenant_id=context.tenant_id,
            )
        except AccountAdminError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return AccountDisabledResponse(user_id=user_id, disabled=disabled)


def _user_id(context: TenantContext) -> UUID:
    try:
        return UUID(context.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Database account is required.") from exc
