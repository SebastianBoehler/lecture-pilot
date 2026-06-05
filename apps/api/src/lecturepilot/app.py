from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from lecturepilot.harness import LecturePilotHarness
from lecturepilot.models import AgentTurnInput, AgentTurnResult
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.sample_data import COURSE, unlocked_lectures


def create_app() -> FastAPI:
    app = FastAPI(title="LecturePilot API", version="0.1.0")
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

    @app.get("/courses/{course_id}/lectures")
    def lectures(course_id: str) -> list[dict]:
        if course_id != COURSE.id:
            raise HTTPException(status_code=404, detail="Course not found.")
        return [item.model_dump(mode="json") for item in unlocked_lectures()]

    @app.post("/agent/turn", response_model=AgentTurnResult)
    async def agent_turn(turn: AgentTurnInput) -> AgentTurnResult:
        try:
            return await LecturePilotHarness().run_turn(turn)
        except ProviderConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    return app


app = create_app()

