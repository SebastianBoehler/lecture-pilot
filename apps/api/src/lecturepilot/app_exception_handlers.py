from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from lecturepilot.canvas_learner_workspace import InvalidLearnerCanvasError
from lecturepilot.client_contract import (
    CLIENT_CONTRACT_HEADER,
    CLIENT_CONTRACT_VERSION,
    CLIENT_UPDATE_REQUIRED_CODE,
    ClientUpdateRequiredError,
)
from lecturepilot.course_canvas_context import InvalidPublishedCanvasContextError
from lecturepilot.course_update_storage import CourseUpdateRecoveryError
from lecturepilot.learner_state import InvalidLearnerQuizStateError
from lecturepilot.quiz_identity import DuplicateCanonicalQuizIdError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CourseUpdateRecoveryError)
    async def course_update_recovery_error(
        _request: Request, exc: CourseUpdateRecoveryError
    ) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    @app.exception_handler(ClientUpdateRequiredError)
    async def client_update_required(
        _request: Request, exc: ClientUpdateRequiredError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"code": CLIENT_UPDATE_REQUIRED_CODE, "detail": str(exc)},
            headers={CLIENT_CONTRACT_HEADER: CLIENT_CONTRACT_VERSION},
        )

    for error_type in (
        InvalidPublishedCanvasContextError,
        InvalidLearnerQuizStateError,
        InvalidLearnerCanvasError,
    ):
        app.add_exception_handler(error_type, _conflict_response)

    @app.exception_handler(DuplicateCanonicalQuizIdError)
    async def duplicate_canonical_quiz_id(
        _request: Request, exc: DuplicateCanonicalQuizIdError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"detail": f"Published canvas has duplicate quiz ID '{exc.quiz_id}'."},
        )


async def _conflict_response(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})
