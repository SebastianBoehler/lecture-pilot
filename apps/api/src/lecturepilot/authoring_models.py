from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from lecturepilot.canvas_models import CanvasDocument


class AuthoringCompletion(BaseModel):
    ready: Literal[True]


class AuthoringMetrics(BaseModel):
    model_requests: int = 0
    tool_calls: int = 0
    validation_failures: int = 0
    repair_edits: int = 0
    quality_reviews: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    elapsed_seconds: float = 0
    resumes: int = 0


@dataclass(frozen=True)
class AuthoringResult:
    document: CanvasDocument
    metrics: AuthoringMetrics


class AuthoringStalledError(RuntimeError):
    """A job repeated the same invalid artifact without making progress."""


class AuthoringDesignConflict(RuntimeError):
    """A critic disputed professor-owned task wording; an author cannot change it."""
