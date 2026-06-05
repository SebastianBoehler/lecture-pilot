from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from lecturepilot.harness import LecturePilotHarness
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
    TuebingenLoginInput,
    TuebingenLoginResult,
)
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.sample_data import COURSE, unlocked_lectures
from lecturepilot.tuebingen_adapter import (
    TuebingenCourseAdapter,
    TuebingenIntegrationUnavailable,
    TuebingenLoginError,
)


def create_app() -> FastAPI:
    app = FastAPI(title="LecturePilot API", version="0.1.0")
    app.state.tuebingen_adapter = TuebingenCourseAdapter()
    app.state.agent_harness = LecturePilotHarness()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/courses")
    def courses() -> list[dict]:
        return [COURSE.model_dump()]

    @app.post("/auth/login", response_model=TuebingenLoginResult)
    def login(input_data: TuebingenLoginInput) -> TuebingenLoginResult:
        try:
            return app.state.tuebingen_adapter.login(
                username=input_data.username,
                password=input_data.password.get_secret_value(),
                term=input_data.term,
            )
        except TuebingenIntegrationUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except TuebingenLoginError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    @app.get("/courses/{course_id}/lectures")
    def lectures(course_id: str) -> list[dict]:
        if course_id != COURSE.id:
            raise HTTPException(status_code=404, detail="Course not found.")
        return [item.model_dump(mode="json") for item in unlocked_lectures()]

    @app.post("/agent/turn", response_model=AgentTurnResult)
    async def agent_turn(turn: AgentTurnInput) -> AgentTurnResult:
        try:
            return await app.state.agent_harness.run_turn(turn)
        except ProviderConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ModelExecutionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    return app


app = create_app()
