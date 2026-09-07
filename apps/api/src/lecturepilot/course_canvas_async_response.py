from fastapi.responses import JSONResponse

from lecturepilot.course_canvas_generation_jobs import CanvasGenerationJob
from lecturepilot.course_canvas_generation_response import CanvasGenerationStatusResponse


def accepted_generation_response(job: CanvasGenerationJob) -> JSONResponse:
    status = CanvasGenerationStatusResponse.model_validate(job.model_dump())
    return JSONResponse(
        status_code=202,
        content=status.model_dump(mode="json", exclude={"canvas": {"workspace_path"}}),
        headers={"Preference-Applied": "respond-async", "X-Generation-Id": job.generation_id},
    )
