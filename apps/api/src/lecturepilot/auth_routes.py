from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request, Response

from lecturepilot.account_models import (
    AccountResponse,
    TuebingenLoginInput,
    TuebingenLoginResult,
)
from lecturepilot.api_auth import request_context
from lecturepilot.database import DatabaseConfigurationError
from lecturepilot.identity_repository import AccountView, IdentityRepository
from lecturepilot.session_auth import SESSION_COOKIE_NAME, SessionAuthSettings
from lecturepilot.session_cookie import attach_session_cookie, clear_session_cookie
from lecturepilot.tenancy import TenantContext
from lecturepilot.tuebingen_adapter import TuebingenIntegrationUnavailable, TuebingenLoginError


def register_auth_routes(app: FastAPI, *, course_tenant_id: str) -> None:
    @app.post("/auth/login", response_model=TuebingenLoginResult)
    def login(input_data: TuebingenLoginInput, response: Response) -> TuebingenLoginResult:
        try:
            identity = app.state.tuebingen_adapter.login(
                username=input_data.username,
                password=input_data.password.get_secret_value(),
                term=input_data.term,
            )
            account = IdentityRepository(app.state.database).record_login(
                identity, tenant_id=course_tenant_id
            )
            issued = app.state.session_store.create(
                account,
                ttl_minutes=SessionAuthSettings.from_env().ttl_minutes,
            )
            attach_session_cookie(response, issued.token)
            return _login_result(account, term=identity.term, csrf_token=issued.csrf_token)
        except TuebingenIntegrationUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except TuebingenLoginError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except DatabaseConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/me", response_model=AccountResponse)
    def current_account(
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> AccountResponse:
        principal = getattr(request.state, "session_principal", None)
        if principal is None:
            raise HTTPException(status_code=401, detail="Database session is required.")
        return _account_response(principal.account)

    @app.post("/auth/logout")
    def logout(request: Request, response: Response) -> dict[str, bool]:
        app.state.session_store.revoke(request.cookies.get(SESSION_COOKIE_NAME))
        clear_session_cookie(response)
        return {"logged_out": True}


def _login_result(account: AccountView, *, term: str, csrf_token: str) -> TuebingenLoginResult:
    return TuebingenLoginResult(
        username=account.username,
        email=account.email,
        term=term,
        tenant_id=account.tenant_id,
        roles=sorted(account.roles, key=lambda role: role.value),
        professor_status=account.professor_status,
        csrf_token=csrf_token,
        courses=list(account.courses),
    )


def _account_response(account: AccountView) -> AccountResponse:
    return AccountResponse(
        user_id=account.user_id,
        username=account.username,
        email=account.email,
        tenant_id=account.tenant_id,
        roles=sorted(account.roles, key=lambda role: role.value),
        professor_status=account.professor_status,
        courses=list(account.courses),
    )
