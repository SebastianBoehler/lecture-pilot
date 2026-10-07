"""Run an owned, renewable exam job independently of the HTTP connection."""

import asyncio
import logging

from fastapi import HTTPException

from lecturepilot.metadata_events import emit_metadata_event
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.practice_exam_generation import generate_practice_exam
from lecturepilot.practice_exam_generation_status import generation_status_response
from lecturepilot.practice_exam_lease import practice_exam_lease
from lecturepilot.practice_exam_models import public_practice_exam
from lecturepilot.practice_exam_planner import PracticeExamPlanningError
from lecturepilot.providers import ProviderConfigurationError


logger = logging.getLogger(__name__)


async def start_exam_generation(app, *, job, request_key, **kwargs):
    tasks = getattr(app.state, "practice_exam_generation_tasks", None)
    if tasks is None:
        tasks = app.state.practice_exam_generation_tasks = {}
    key = (job.generation_id, job.attempt)
    task = asyncio.create_task(_generate_owned(app, job=job, request_key=request_key, **kwargs))
    tasks[key] = task

    def finished(completed):
        tasks.pop(key, None)
        if not completed.cancelled():
            completed.exception()  # The durable job owns safe failure details after disconnect.

    task.add_done_callback(finished)
    try:
        return await asyncio.wait_for(asyncio.shield(task), timeout=1)
    except TimeoutError:
        return generation_status_response(job)


async def _generate_owned(app, *, job, request_key, context, input_data, **kwargs):
    store = app.state.practice_exam_generation_store
    error_code = "unexpected_error"
    try:
        async with practice_exam_lease(
            store, job, user_id=context.user_id, request_key=request_key
        ):
            exam = await generate_practice_exam(
                app, context=context, input_data=input_data, **kwargs
            )
        await asyncio.to_thread(
            app.state.practice_exam_store.write,
            user_id=context.user_id,
            course_id=job.course_id,
            exam=exam,
        )
        await asyncio.to_thread(
            store.complete, job, user_id=context.user_id, request_key=request_key, exam_id=exam.id
        )
        emit_metadata_event(
            "practice_exam.generated",
            question_count=len(exam.questions),
            ppi_source_count=len(input_data.ppi_source_ids),
            status="completed",
        )
        return public_practice_exam(exam)
    except HTTPException as exc:
        error_code = "quota_exceeded" if exc.status_code == 429 else "source_error"
        raise
    except ProviderConfigurationError as exc:
        error_code = "provider_configuration_error"
        raise HTTPException(
            status_code=503, detail="Practice exam provider is unavailable."
        ) from exc
    except ModelExecutionError as exc:
        error_code = "model_execution_error"
        raise HTTPException(
            status_code=502, detail="Practice exam generation failed. Please retry."
        ) from exc
    except PracticeExamPlanningError as exc:
        error_code = "invalid_model_output"
        raise HTTPException(
            status_code=502, detail="Practice exam generation failed validation. Please retry."
        ) from exc
    except asyncio.CancelledError:
        error_code = "cancelled"
        raise
    except Exception:
        logger.exception("Practice exam generation failed")
        raise
    finally:
        current = await asyncio.to_thread(
            store.read, user_id=context.user_id, course_id=job.course_id, request_key=request_key
        )
        if current and current.status == "running" and current.attempt == job.attempt:
            await asyncio.to_thread(
                store.fail,
                job,
                user_id=context.user_id,
                request_key=request_key,
                error_code=error_code,
            )
