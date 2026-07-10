from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response, status

from lecturepilot.account_models import (
    LocalProfessorLoginInput,
    LocalProfessorRegistrationInput,
    LoginResult,
)
from lecturepilot.account_responses import login_result
from lecturepilot.database import DatabaseConfigurationError
from lecturepilot.identity_repository import AccountView
from lecturepilot.professor_identity_repository import (
    ProfessorAuthenticationError,
    ProfessorIdentityRepository,
    ProfessorRegistrationError,
)
from lecturepilot.session_auth import SessionAuthSettings
from lecturepilot.session_cookie import attach_session_cookie


def register_professor_auth_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    default_term: str,
) -> None:
    @app.post(
        "/auth/professor/register",
        response_model=LoginResult,
        status_code=status.HTTP_201_CREATED,
    )
    def register_professor(
        input_data: LocalProfessorRegistrationInput,
        response: Response,
    ) -> LoginResult:
        try:
            account = ProfessorIdentityRepository(app.state.database).register(
                display_name=input_data.display_name,
                email=str(input_data.email),
                password=input_data.password.get_secret_value(),
                tenant_id=course_tenant_id,
            )
            return _issue_session(app, response, account, default_term)
        except ProfessorRegistrationError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except DatabaseConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/auth/professor/login", response_model=LoginResult)
    def login_professor(
        input_data: LocalProfessorLoginInput,
        response: Response,
    ) -> LoginResult:
        try:
            account = ProfessorIdentityRepository(app.state.database).authenticate(
                email=str(input_data.email),
                password=input_data.password.get_secret_value(),
                tenant_id=course_tenant_id,
            )
            return _issue_session(app, response, account, default_term)
        except ProfessorAuthenticationError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except DatabaseConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc


def _issue_session(
    app: FastAPI,
    response: Response,
    account: AccountView,
    term: str,
) -> LoginResult:
    issued = app.state.session_store.create(
        account,
        ttl_minutes=SessionAuthSettings.from_env().ttl_minutes,
    )
    attach_session_cookie(response, issued.token)
    return login_result(account, term=term, csrf_token=issued.csrf_token)
