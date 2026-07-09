from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response

from lecturepilot.demo_course_access import include_created_courses_for_demo
from lecturepilot.models import TuebingenLoginInput, TuebingenLoginResult
from lecturepilot.session_auth import SessionAuthError
from lecturepilot.session_cookie import attach_session_cookie, clear_session_cookie
from lecturepilot.tuebingen_adapter import TuebingenIntegrationUnavailable, TuebingenLoginError


def register_auth_routes(app: FastAPI, *, course_tenant_id: str) -> None:
    @app.post("/auth/login", response_model=TuebingenLoginResult)
    def login(input_data: TuebingenLoginInput, response: Response) -> TuebingenLoginResult:
        try:
            result = app.state.tuebingen_adapter.login(
                username=input_data.username,
                password=input_data.password.get_secret_value(),
                term=input_data.term,
            )
            result = include_created_courses_for_demo(
                result,
                tenant_id=course_tenant_id,
                workspace_root=app.state.canvas_workspace.workspace_root,
            )
            return attach_session_cookie(response, result)
        except TuebingenIntegrationUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except TuebingenLoginError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except SessionAuthError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/auth/logout")
    def logout(response: Response) -> dict[str, bool]:
        return clear_session_cookie(response)
