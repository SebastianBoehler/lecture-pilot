from __future__ import annotations

import json
import logging
from threading import current_thread
from types import SimpleNamespace

import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_planner import CourseCanvasPlanner
from lecturepilot.course_canvas_generation import generate_course_canvas_draft
from lecturepilot.logging_observability import (
    LOGGER_NAME,
    LoggingObservability,
    current_operation_id,
)
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.providers import ProviderConfigurationError, ProviderRegistry
from lecturepilot.source_bundle_canvas import SourceBundleCanvasError
from lecturepilot.tenancy import TenantContext


async def test_source_resolution_failure_logs_generation_stage_without_content(
    caplog,
) -> None:
    app = SimpleNamespace(state=SimpleNamespace(observability=LoggingObservability()))
    context = TenantContext(
        tenant_id="tenant-tuebingen",
        user_id="professor-1",
        roles=frozenset(),
    )
    event_loop_thread = current_thread()

    def fail_source(_course_id: str, _lecture_id: str):
        assert current_thread() is not event_loop_thread
        assert current_operation_id() is not None
        raise SourceBundleCanvasError("PRIVATE uploads/course/Lecture02.tex")

    with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
        with pytest.raises(SourceBundleCanvasError):
            await generate_course_canvas_draft(
                app,
                course_id="course-1",
                lecture_id="lecture-02",
                context=context,
                source_document=fail_source,
                generation_id="generation-id-0000000000000000001",
                attempt=1,
            )

    payloads = [
        json.loads(record.message) for record in caplog.records if record.name == LOGGER_NAME
    ]
    assert [payload["stage"] for payload in payloads] == ["source_resolve", "request"]
    assert {payload["operation_id"] for payload in payloads} == {payloads[0]["generation_id"]}
    assert all(payload["course_id"] == "course-1" for payload in payloads)
    assert all(payload["lecture_id"] == "lecture-02" for payload in payloads)
    assert all(payload["attempt"] == 1 for payload in payloads)
    assert all(payload["exception_type"] == "SourceBundleCanvasError" for payload in payloads)
    assert "PRIVATE" not in " ".join(record.message for record in caplog.records)


async def test_course_planner_logs_model_retry_attempts_without_error_messages(
    monkeypatch, caplog
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    planner = CourseCanvasPlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=_FailingPlanClient(),
        observability=LoggingObservability(),
    )

    with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
        with pytest.raises(ModelExecutionError):
            await planner.plan_canvas(_source_document())

    payloads = [
        json.loads(record.message) for record in caplog.records if record.name == LOGGER_NAME
    ]
    assert [payload["attempt"] for payload in payloads] == [1, 2]
    assert len({payload["generation_id"] for payload in payloads}) == 1
    assert all(payload["course_id"] == "martius-ml" for payload in payloads)
    assert all(payload["lecture_id"] == "lecture-03" for payload in payloads)
    assert all(payload["provider"] == "gemini" for payload in payloads)
    assert all(payload["model"] == "gemini/test-model" for payload in payloads)
    assert [payload["exception_type"] for payload in payloads] == [
        "ProviderConfigurationError",
        "ModelExecutionError",
    ]
    assert "PRIVATE" not in " ".join(record.message for record in caplog.records)


class _FailingPlanClient:
    def __init__(self) -> None:
        self.calls = 0

    async def complete_plan(self, *, settings, messages):
        self.calls += 1
        if self.calls == 1:
            raise ProviderConfigurationError("PRIVATE invalid model response")
        raise ModelExecutionError("PRIVATE provider failure")


def _source_document() -> CanvasDocument:
    return CanvasDocument(
        id="martius-ml-lecture-03",
        course_id="martius-ml",
        lecture_id="lecture-03",
        title="Bayesian Decision Theory",
        source_kind="latex",
        source_ref="Lecture03.tex",
        workspace_path="course-planner/lecture-03/source.json",
        sections=[
            CanvasSection(
                id="source-risk",
                title="Risk",
                source_ref="Lecture03.tex frame 8",
                blocks=[
                    CanvasBlock(
                        id="source-risk-p",
                        type="paragraph",
                        text="Risk source evidence.",
                    )
                ],
            )
        ],
    )
