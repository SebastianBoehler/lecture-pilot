from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request, Response

from lecturepilot.account_models import (
    AccountResponse,
    LoginResult,
    TuebingenLoginInput,
)
from lecturepilot.account_responses import account_response, login_result
from lecturepilot.api_auth import request_context
from lecturepilot.auth_diagnostics import (
    AUTH_ATTEMPT_HEADER,
    AuthDiagnostics,
    auth_diagnostic_attempt,
    referenced_error,
)
from lecturepilot.database import DatabaseConfigurationError
from lecturepilot.identity_repository import IdentityRepository
from lecturepilot.session_auth import SESSION_COOKIE_NAME, SessionAuthSettings
from lecturepilot.session_cookie import attach_session_cookie, clear_session_cookie
from lecturepilot.tenancy import TenantContext
from lecturepilot.tuebingen_adapter import TuebingenIntegrationUnavailable, TuebingenLoginError


def register_auth_routes(app: FastAPI, *, course_tenant_id: str) -> None:
    @app.post("/auth/login", response_model=LoginResult)
    def login(input_data: TuebingenLoginInput, response: Response) -> LoginResult:
        with auth_diagnostic_attempt(input_data.username) as diagnostics:
            login_started = diagnostics.started("lecturepilot.login")
            try:
                adapter_started = diagnostics.started("university.adapter")
                try:
                    identity = app.state.tuebingen_adapter.login(
                        username=input_data.username,
                        password=input_data.password.get_secret_value(),
                        term=input_data.term,
                    )
                except Exception as exc:
                    diagnostics.failed("university.adapter", adapter_started, exc)
                    raise
                diagnostics.succeeded(
                    "university.adapter",
                    adapter_started,
                    current_role=identity.alma_current_role,
                    available_roles=identity.alma_available_roles,
                    course_count=len(identity.courses),
                    source_count=len(identity.sources_checked),
                    warning_count=len(identity.warnings),
                )
                database_started = diagnostics.started("database.identity_sync")
                try:
                    account = IdentityRepository(app.state.database).record_login(
                        identity, tenant_id=course_tenant_id
                    )
                except Exception as exc:
                    diagnostics.failed("database.identity_sync", database_started, exc)
                    raise
                diagnostics.succeeded(
                    "database.identity_sync",
                    database_started,
                    account_type=account.account_type,
                    role_count=len(account.roles),
                    course_count=len(account.courses),
                )
                session_started = diagnostics.started("session.issue")
                try:
                    issued = app.state.session_store.create(
                        account,
                        ttl_minutes=SessionAuthSettings.from_env().ttl_minutes,
                    )
                    attach_session_cookie(response, issued.token)
                except Exception as exc:
                    diagnostics.failed("session.issue", session_started, exc)
                    raise
                response.headers[AUTH_ATTEMPT_HEADER] = diagnostics.attempt_id
                diagnostics.succeeded("session.issue", session_started)
                diagnostics.succeeded(
                    "lecturepilot.login",
                    login_started,
                    account_type=account.account_type,
                    current_role=identity.alma_current_role,
                )
                return login_result(account, term=identity.term, csrf_token=issued.csrf_token)
            except TuebingenIntegrationUnavailable as exc:
                diagnostics.failed("lecturepilot.login", login_started, exc)
                raise _login_error(503, str(exc), diagnostics) from exc
            except TuebingenLoginError as exc:
                diagnostics.failed("lecturepilot.login", login_started, exc)
                raise _login_error(401, str(exc), diagnostics) from exc
            except PermissionError as exc:
                diagnostics.failed("lecturepilot.login", login_started, exc)
                raise _login_error(403, str(exc), diagnostics) from exc
            except DatabaseConfigurationError as exc:
                diagnostics.failed("lecturepilot.login", login_started, exc)
                raise _login_error(503, str(exc), diagnostics) from exc
            except Exception as exc:
                diagnostics.failed("lecturepilot.login", login_started, exc)
                raise

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
        app.state.session_store.revoke(request.cookies.get(SESSION_COOKIE_NAME))
        clear_session_cookie(response)
        return {"logged_out": True}


def _login_error(
    status_code: int,
    detail: str,
    diagnostics: AuthDiagnostics,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=referenced_error(detail, diagnostics),
        headers={AUTH_ATTEMPT_HEADER: diagnostics.attempt_id},
    )
