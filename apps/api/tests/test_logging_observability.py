from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml

from lecturepilot.logging_observability import LOGGER_NAME, logger, operation_scope
from lecturepilot.metadata_events import configure_metadata_file_logging
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.observability import observability_from_env


def test_logging_observability_emits_allowlisted_metadata_only(monkeypatch, caplog) -> None:
    monkeypatch.setenv("LECTUREPILOT_OBSERVABILITY", "logging")
    monkeypatch.setenv("LECTUREPILOT_TRACE_CONTENT", "metadata")
    observability = observability_from_env()

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        with (
            operation_scope("generation-123"),
            observability.model_span(
                course_id="course-1",
                lecture_id="lecture-2",
                stage="primary_plan",
                attempt=2,
                provider="gemini",
                model="gemini/gemini-3.1-flash-lite",
                prompt="PRIVATE PROMPT",
                source_content="PRIVATE SOURCE",
                api_key="PRIVATE CREDENTIAL",
            ) as span,
        ):
            span.set_outputs(
                {
                    "section_count": 8,
                    "error": "PRIVATE PROVIDER RESPONSE",
                    "canvas_commands": ["PRIVATE" * 40],
                }
            )

    records = [record for record in caplog.records if record.name == LOGGER_NAME]
    assert len(records) == 2
    started = json.loads(records[0].message)
    payload = json.loads(records[1].message)
    assert started["event"] == "observability.span_started"
    assert started["status"] == "started"
    assert payload["attempt"] == 2
    assert payload["course_id"] == "course-1"
    assert payload["event"] == "observability.span_finished"
    assert payload["lecture_id"] == "lecture-2"
    assert payload["model"] == "gemini/gemini-3.1-flash-lite"
    assert payload["operation_id"] == "generation-123"
    assert payload["provider"] == "gemini"
    assert payload["section_count"] == 8
    assert payload["span"] == "lecturepilot.call_model"
    assert payload["span_type"] == "LLM"
    assert payload["stage"] == "primary_plan"
    assert payload["status"] == "ok"
    assert "canvas_commands" not in payload
    assert payload["latency_ms"] >= 0
    assert "PRIVATE" not in records[0].message


def test_logging_observability_records_exception_class_without_message(monkeypatch, caplog) -> None:
    monkeypatch.setenv("LECTUREPILOT_OBSERVABILITY", "logging")
    observability = observability_from_env()

    with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
        try:
            with (
                operation_scope("generation-456"),
                observability.tool_span(
                    "course_canvas_generation",
                    course_id="course-1",
                    lecture_id="lecture-2",
                    stage="source_resolve",
                    attempt=1,
                ),
            ):
                try:
                    raise TimeoutError("PRIVATE SOCKET ADDRESS")
                except TimeoutError as cause:
                    raise ModelExecutionError("PRIVATE PROVIDER MESSAGE") from cause
        except ModelExecutionError:
            pass

    payload = json.loads(caplog.records[-1].message)
    assert payload["exception_type"] == "ModelExecutionError"
    assert payload["root_cause_type"] == "TimeoutError"
    assert payload["status"] == "error"
    assert payload["operation_id"] == "generation-456"
    assert "PRIVATE" not in caplog.records[-1].message


def test_logging_observability_reserves_operational_status(monkeypatch, caplog) -> None:
    monkeypatch.setenv("LECTUREPILOT_OBSERVABILITY", "logging")
    observability = observability_from_env()

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        with observability.tool_span("quality_gate", status="passed"):
            pass

    payload = json.loads(caplog.records[-1].message)
    assert payload["status"] == "ok"
    assert "passed" not in caplog.records[-1].message


def test_logging_observability_uses_uvicorn_pipeline_without_own_handlers() -> None:
    assert LOGGER_NAME.startswith("uvicorn.error.")
    assert logger.handlers == []


def test_production_compose_enables_metadata_only_logging() -> None:
    compose_path = Path(__file__).resolve().parents[3] / "deploy" / "compose.yml"
    environment = yaml.safe_load(compose_path.read_text(encoding="utf-8"))["x-api-environment"]

    assert environment["LECTUREPILOT_OBSERVABILITY"] == "logging"
    assert environment["LECTUREPILOT_TRACE_CONTENT"] == "metadata"


def test_metadata_file_logging_keeps_fourteen_calendar_files(tmp_path, monkeypatch) -> None:
    path = tmp_path / "metadata.jsonl"
    monkeypatch.setenv("LECTUREPILOT_METADATA_LOG_PATH", str(path))

    configure_metadata_file_logging()

    handler = next(
        item
        for item in logger.handlers
        if getattr(item, "lecturepilot_log_path", None) == str(path)
    )
    assert handler.backupCount == 13
    assert logger.propagate is False
    logger.removeHandler(handler)
    handler.close()
    logger.propagate = True
