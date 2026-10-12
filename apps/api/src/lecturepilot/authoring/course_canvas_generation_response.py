from datetime import datetime

from pydantic import BaseModel

from lecturepilot.canvas.canvas_models import CanvasDocument
from lecturepilot.authoring.authoring_models import AuthoringMetrics
from lecturepilot.authoring.course_canvas_generation_jobs import GenerationStatus


class CanvasGenerationStatusResponse(BaseModel):
    generation_id: str
    status: GenerationStatus
    attempt: int
    updated_at: datetime
    error_code: str | None = None
    error_detail: str | None = None
    repairable: bool = False
    canvas: CanvasDocument | None = None
    authoring_metrics: AuthoringMetrics | None = None
