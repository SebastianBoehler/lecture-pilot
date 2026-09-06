from contextlib import asynccontextmanager
import re

from pydantic_ai.models.function import FunctionModel

from lecturepilot.authoring_runtime import CourseCanvasAuthor
from lecturepilot.course_canvas_quality import CanvasQualityReviewer


def install_author(client, monkeypatch, respond, reviewer):
    @asynccontextmanager
    async def model(*args, **kwargs):
        yield FunctionModel(respond)

    monkeypatch.setattr("lecturepilot.authoring_runtime.authoring_model", model)
    author = CourseCanvasAuthor()
    author.reviewer = CanvasQualityReviewer(reviewer)
    client.app.state.course_planner = author


def assigned_drafts(info):
    return list(dict.fromkeys(re.findall(r"'(/draft/[^']+\.md)'", info.instructions)))
