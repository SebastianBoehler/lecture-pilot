from pydantic import BaseModel


class PracticeExamGenerationStatusResponse(BaseModel):
    generation_id: str
    status: str
    attempt: int
    error_code: str | None = None
    exam_id: str | None = None


def generation_status_response(job):
    return PracticeExamGenerationStatusResponse(**job.model_dump())
