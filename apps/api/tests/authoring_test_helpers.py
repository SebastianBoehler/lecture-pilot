from contextlib import asynccontextmanager
import re

from pydantic_ai.models.function import FunctionModel

from lecturepilot.authoring_runtime import CourseCanvasAuthor
from lecturepilot.course_canvas_quality import CanvasQualityReviewer


def install_author(client, monkeypatch, respond, reviewer):
    monkeypatch.setenv("LECTUREPILOT_MODEL", "openai/authoring-test")
    monkeypatch.setenv("LECTUREPILOT_ALLOWED_MODELS", "openai/authoring-test")
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-function-model")

    @asynccontextmanager
    async def model(*args, **kwargs):
        yield FunctionModel(respond)

    monkeypatch.setattr("lecturepilot.authoring_runtime.authoring_model", model)
    author = CourseCanvasAuthor()
    author.reviewer = CanvasQualityReviewer(reviewer)
    client.app.state.course_planner = author


def assigned_drafts(info):
    return list(dict.fromkeys(re.findall(r"'(/draft/[^']+\.md)'", info.instructions)))
