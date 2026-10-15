from fastapi import FastAPI, HTTPException, Request
from sqlalchemy.exc import IntegrityError

from lecturepilot.database import DatabaseConfigurationError
from lecturepilot.identity.account_email import AccountEmailError, send_account_email
from lecturepilot.identity.csrf import allowed_origins
from lecturepilot.identity.local_account_models import (
    EmailInput,
    RegistrationInput,
    ResetPasswordInput,
    TokenInput,
)
from lecturepilot.identity.local_accounts import LocalAccounts


_MESSAGE = {"message": "If this address is eligible, an email with the next step has been sent."}


def check_auth_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if (origin and origin.rstrip("/") not in allowed_origins()) or request.headers.get(
        "sec-fetch-site"
    ) == "cross-site":
        raise HTTPException(403, "Request origin is not allowed.")


def register_local_account_routes(app: FastAPI, *, tenant_id: str) -> None:
    def repository() -> LocalAccounts:
        return LocalAccounts(app.state.database, tenant_id)

    def challenge(email: str, purpose: str, password: str | None = None):
        try:
            token = repository().challenge(email, purpose, password)
            if token:
                send_account_email(email, purpose, token)
            return _MESSAGE
        except (AccountEmailError, DatabaseConfigurationError) as exc:
            raise HTTPException(503, str(exc)) from exc
        except IntegrityError as exc:
            raise HTTPException(409, "Another request is in progress. Please try again.") from exc

    def confirm(token: str, purpose: str, password: str | None = None):
        try:
            repository().confirm(token, purpose, password)
            return {"message": "Account updated. You can now sign in."}
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except DatabaseConfigurationError as exc:
            raise HTTPException(503, str(exc)) from exc
        except IntegrityError as exc:
            raise HTTPException(
                409, "Account already registered. Sign in or reset your password."
            ) from exc

    @app.post("/auth/register")
    def register(input_data: RegistrationInput, request: Request):
        check_auth_origin(request)
        return challenge(input_data.email, "verify", input_data.password.get_secret_value())

    @app.post("/auth/verify")
    def verify(input_data: TokenInput, request: Request):
        check_auth_origin(request)
        return confirm(input_data.token.get_secret_value(), "verify")

    @app.post("/auth/password-reset")
    def password_reset(input_data: EmailInput, request: Request):
        check_auth_origin(request)
        return challenge(input_data.email, "reset")

    @app.post("/auth/password-reset/confirm")
    def reset_confirm(input_data: ResetPasswordInput, request: Request):
        check_auth_origin(request)
        return confirm(
            input_data.token.get_secret_value(), "reset", input_data.password.get_secret_value()
        )
