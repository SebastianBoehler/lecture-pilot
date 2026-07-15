from __future__ import annotations

from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response

from lecturepilot.account_models import (
    AccountResponse,
    LoginResult,
    TuebingenLoginInput,
)
from lecturepilot.account_responses import account_response, login_result
from lecturepilot.api_auth import request_context
from lecturepilot.database import DatabaseConfigurationError
from lecturepilot.identity_repository import IdentityRepository
from lecturepilot.session_auth import SESSION_COOKIE_NAME, SessionAuthSettings
from lecturepilot.session_cookie import attach_session_cookie, clear_session_cookie
from lecturepilot.tenancy import TenantContext
from lecturepilot.tuebingen_adapter import (
    PendingUniversityLogin,
    TuebingenIntegrationUnavailable,
    TuebingenLoginError,
)


def register_auth_routes(app: FastAPI, *, course_tenant_id: str) -> None:
    @app.post("/auth/login", response_model=LoginResult)
    def login(
        input_data: TuebingenLoginInput,
        response: Response,
        background_tasks: BackgroundTasks,
    ) -> LoginResult:
        with app.state.observability.tool_span("auth_login") as span:
            try:
                pending = app.state.tuebingen_adapter.authenticate(
                    username=input_data.username,
                    password=input_data.password.get_secret_value(),
                    term=input_data.term,
                )
                identity = pending.initial_identity
                sync_id = uuid4().hex
                account = IdentityRepository(app.state.database).begin_login(
                    identity,
                    tenant_id=course_tenant_id,
                    sync_id=sync_id,
                )
                issued = app.state.session_store.create(
                    account,
                    ttl_minutes=SessionAuthSettings.from_env().ttl_minutes,
                )
                attach_session_cookie(response, issued.token)
                background_tasks.add_task(
                    _complete_university_sync,
                    app,
                    pending,
                    course_tenant_id,
                    sync_id,
                )
                span.set_outputs({"account_type": account.account_type, "outcome": "success"})
                return login_result(account, term=identity.term, csrf_token=issued.csrf_token)
            except TuebingenIntegrationUnavailable as exc:
                span.set_outputs({"outcome": "error", "reason": "integration_unavailable"})
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            except TuebingenLoginError as exc:
                span.set_outputs({"outcome": "error", "reason": "invalid_credentials"})
                raise HTTPException(status_code=401, detail=str(exc)) from exc
            except PermissionError as exc:
                span.set_outputs({"outcome": "error", "reason": "account_forbidden"})
                raise HTTPException(status_code=403, detail=str(exc)) from exc
            except DatabaseConfigurationError as exc:
                span.set_outputs({"outcome": "error", "reason": "database_unavailable"})
                raise HTTPException(status_code=503, detail=str(exc)) from exc

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


def _complete_university_sync(
    app: FastAPI,
    pending: PendingUniversityLogin,
    tenant_id: str,
    sync_id: str,
) -> None:
    repository = IdentityRepository(app.state.database)
    try:
        with app.state.observability.tool_span("university_course_sync") as span:
            identity = pending.synchronize()
            applied = repository.complete_course_sync(
                identity,
                tenant_id=tenant_id,
                sync_id=sync_id,
            )
            span.set_outputs(
                {
                    "applied": applied,
                    "course_count": len(identity.courses),
                    "outcome": (
                        "ready"
                        if applied and identity.sources_checked
                        else "no_sources"
                        if applied
                        else "superseded"
                    ),
                    "source_count": len(identity.sources_checked),
                    "warning_count": len(identity.warnings),
                }
            )
    except Exception:
        repository.fail_course_sync(
            username=pending.initial_identity.username,
            sync_id=sync_id,
        )
        return
