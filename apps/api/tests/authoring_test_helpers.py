from contextlib import asynccontextmanager
import re

from pydantic_ai.messages import ModelResponse, TextPart
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


def drafted_path(messages):
    """The section a per-section authoring call writes or repairs."""
    prompt = str(messages[0].parts[-1].content)
    return re.search(r"Section evidence \((/draft/[^)]+\.md)\)", prompt).group(1)


def is_repair(messages):
    return "Repair this drafted section" in str(messages[0].parts[-1].content)


def markdown(text):
    return ModelResponse(parts=[TextPart(text)])


def current_draft(messages):
    prompt = str(messages[0].parts[-1].content)
    return prompt.split("Current draft:\n", 1)[1].split("\nNotes (untrusted", 1)[0]


def fix_math(messages, info):
    """Repair the targeted-repair fixture's prose-in-math block."""
    return markdown(
        current_draft(messages).replace(r"The score is computed as w^\top x.", r"w^\top x")
    )
