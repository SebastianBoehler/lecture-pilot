from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import current_thread
from types import SimpleNamespace

import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_canvas_generation import generate_course_canvas_draft
from lecturepilot.logging_observability import (
    LOGGER_NAME,
    LoggingObservability,
    current_operation_id,
)
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.source_bundle_canvas import SourceBundleCanvasError
from lecturepilot.tenancy import TenantContext


async def test_source_resolution_failure_logs_generation_stage_without_content(
    caplog,
    tmp_path: Path,
) -> None:
    app = SimpleNamespace(
        state=SimpleNamespace(
            observability=LoggingObservability(),
            canvas_workspace=CanvasWorkspace(
                workspace_root=tmp_path / "workspaces",
                material_root=tmp_path / "materials",
            ),
        )
    )
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


class _FailingPlanClient:
    def __init__(self) -> None:
        self.calls = 0

    async def complete_plan(self, *, settings, messages, response_format=None):
        self.calls += 1
        if self.calls == 1:
            raise CanvasGenerationRepairableError("PRIVATE invalid model response")
        raise ModelExecutionError("PRIVATE provider failure")


class _RepairingSectionPlanClient:
    def __init__(self) -> None:
        self.calls = 0

    async def complete_plan(self, *, settings, messages, response_format=None):
        self.calls += 1
        if self.calls == 1:
            return {"sections": [{"title": "PRIVATE invalid", "blocks": []}]}
        return {
            "sections": [
                {
                    "title": "Risk",
                    "source_ref": "Lecture03.tex frame 8",
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text": "A source-grounded explanation of risk.",
                        },
                        {
                            "type": "checkpoint",
                            "id": "practice-derive-conclusion",
                            "text": "Derive the conclusion from the stated evidence and justify the reasoning.",
                        },
                    ],
                }
            ]
        }


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
