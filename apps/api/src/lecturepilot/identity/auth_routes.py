from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request, Response

from lecturepilot.identity.auth_validation import register_auth_validation
from lecturepilot.identity.account_models import AccountResponse, LoginResult
from lecturepilot.identity.account_responses import account_response, login_result
from lecturepilot.identity.api_auth import request_context
from lecturepilot.database import DatabaseConfigurationError
from lecturepilot.identity.local_account_models import PasswordLoginInput
from lecturepilot.identity.local_accounts import LocalAccounts
from lecturepilot.identity.local_account_routes import (
    check_auth_origin,
    register_local_account_routes,
)
from lecturepilot.identity.session_auth import SESSION_COOKIE_NAME, SessionAuthSettings
from lecturepilot.identity.session_cookie import attach_session_cookie, clear_session_cookie
from lecturepilot.identity.tenancy import TenantContext


def register_auth_routes(app: FastAPI, *, course_tenant_id: str) -> None:
    register_auth_validation(app)
    register_local_account_routes(app, tenant_id=course_tenant_id)

    @app.post("/auth/login", response_model=LoginResult)
    def login(input_data: PasswordLoginInput, request: Request, response: Response) -> LoginResult:
        check_auth_origin(request)
        with app.state.observability.tool_span("auth_login") as span:
            try:
                result = LocalAccounts(app.state.database, course_tenant_id).sign_in(
                    input_data.email,
                    input_data.password.get_secret_value(),
                    app.state.session_store,
                    ttl_minutes=SessionAuthSettings.from_env().ttl_minutes,
                )
                if result is None:
                    span.set_outputs({"outcome": "error", "reason": "invalid_credentials"})
                    raise HTTPException(
                        401, "Email or password is incorrect, or email is not verified."
                    )
                account, issued = result
                attach_session_cookie(response, issued.token)
                span.set_outputs({"outcome": "success", "account_type": account.account_type})
                return login_result(account, term="", csrf_token=issued.csrf_token)
            except DatabaseConfigurationError as exc:
                span.set_outputs({"outcome": "error", "reason": "database_unavailable"})
                raise HTTPException(503, str(exc)) from exc

    @app.get("/me", response_model=AccountResponse)
    def current_account(
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> AccountResponse:
        principal = getattr(request.state, "session_principal", None)
        if principal is None:
            raise HTTPException(status_code=401, detail="Database session is required.")
        return account_response(principal.account)

    @app.post("/auth/logout")
    def logout(request: Request, response: Response) -> dict[str, bool]:
        with app.state.observability.tool_span("auth_logout") as span:
            termination = app.state.session_store.revoke(request.cookies.get(SESSION_COOKIE_NAME))
            clear_session_cookie(response)
            span.set_outputs(
                {
                    "duration_ms": termination.duration_ms if termination else None,
                    "outcome": "revoked" if termination else "no_active_session",
                    "reason": termination.reason if termination else "missing_or_revoked",
                }
            )
            return {"logged_out": True}
