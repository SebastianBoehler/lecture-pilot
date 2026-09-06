"""Paid authoring comparison on approved private course snapshots; no publication."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from hashlib import sha256
from importlib.metadata import version
import json
import logging
import os
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from uuid import uuid4

from dotenv import load_dotenv


class Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.events = []

    def emit(self, record):
        try:
            self.events.append(json.loads(record.getMessage()))
        except ValueError:
            pass


async def main(args):
    import lecturepilot
    from lecturepilot.authoring_job import AuthoringJob, run_authoring_job
    from lecturepilot.authoring_provider import authoring_model
    from lecturepilot.canvas_internal_serialization import (
        canvas_document_internal_payload,
    )
    from lecturepilot.canvas_models import CanvasDocument
    from lecturepilot.canvas_workspace import CanvasWorkspace
    from lecturepilot.course_builder_source import course_builder_source_document
    from lecturepilot.course_canvas_planner import CourseCanvasPlanner
    from lecturepilot.course_canvas_quality import CanvasQualityReviewer
    from lecturepilot.course_canvas_repairs import lecture_source_revision
    from lecturepilot.course_practice_design_models import PracticeDesign
    from lecturepilot.course_practice_design_store import PracticeDesignStore
    from lecturepilot.course_content_filter import filter_source_document_for_planning
    from lecturepilot.course_media import course_media_evidence
    from lecturepilot.durable_files import atomic_write_json
    from lecturepilot.metadata_events import LOGGER_NAME, operation_scope
    from lecturepilot.models import ProviderCapability
    from lecturepilot.providers import ProviderRegistry

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    registry = ProviderRegistry.from_env()
    settings = registry.require_ready(
        [ProviderCapability.CHAT, ProviderCapability.TOOL_CALLS]
    )
    workspace = CanvasWorkspace(workspace_root=args.workspace.resolve())
    app = SimpleNamespace(state=SimpleNamespace(canvas_workspace=workspace))
    capture = Capture()
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.addHandler(capture)
    semaphore = asyncio.Semaphore(3)
    code_root = Path(lecturepilot.__file__).resolve().parent
    code_digest = sha256()
    for module in sorted(code_root.glob("*.py")):
        code_digest.update(module.name.encode() + b"\0" + module.read_bytes())
    environment = {
        "api_source_sha256": code_digest.hexdigest(),
        "packages": {
            package: version(package)
            for package in ("pydantic-ai-slim", "openai", "litellm")
        },
    }

    async def run_one(lecture):
        async with semaphore:
            job_id = uuid4().hex
            case = output / args.course / lecture
            snapshot = case / "input.json"
            prepared = perf_counter()
            if snapshot.exists():
                payload = json.loads(snapshot.read_text())
                source = CanvasDocument.model_validate(payload["source"])
                design = PracticeDesign.model_validate_json(
                    json.dumps(payload["design"])
                )
                revision = payload["source_revision"]
            else:
                source = await asyncio.to_thread(
                    course_builder_source_document, app, args.course, lecture
                )
                revision = lecture_source_revision(
                    workspace.layout, course_id=args.course, lecture_id=lecture
                )
                design = PracticeDesignStore(workspace.layout).require_approved(
                    course_id=args.course,
                    lecture_id=lecture,
                    source_revision=revision,
                )
                source = course_media_evidence(
                    source, workspace.course_media_root(args.course)
                )
                source = filter_source_document_for_planning(source)
                atomic_write_json(
                    snapshot,
                    {
                        "source": canvas_document_internal_payload(source),
                        "design": design.model_dump(mode="json"),
                        "source_revision": revision,
                    },
                )
            row = {
                "started_at": datetime.now(UTC).isoformat(),
                "environment": environment,
                "engine": args.engine,
                "model": settings.model,
                "course": args.course,
                "lecture": lecture,
                "job_id": job_id,
                "preparation_seconds": perf_counter() - prepared,
                "source_revision": revision,
                "design_revision": design.revision,
            }
            started = perf_counter()
            with operation_scope(job_id):
                try:
                    if args.engine == "baseline":
                        document = await CourseCanvasPlanner(
                            provider_registry=registry
                        ).plan_canvas(
                            source,
                            practice_design=design,
                            output_language=args.language,
                        )
                    else:
                        job = AuthoringJob(
                            root=case / job_id,
                            source=source,
                            design=design,
                            source_revision=revision,
                            settings=settings,
                            reviewer=CanvasQualityReviewer(),
                            output_language=args.language,
                        )
                        async with authoring_model(
                            settings, None, job.authorize
                        ) as model:
                            result = await run_authoring_job(job, model=model)
                        document = result.document
                        row["agent_metrics"] = result.metrics.model_dump()
                    row["success"] = True
                    atomic_write_json(
                        case / f"{args.engine}-{job_id}-canvas.json",
                        canvas_document_internal_payload(document),
                    )
                except Exception as exc:
                    row.update(
                        success=False, error_type=type(exc).__name__, error=str(exc)
                    )
                    if exc.__cause__:
                        atomic_write_json(
                            case / f"{args.engine}-{job_id}-error.json",
                            {"cause": str(exc.__cause__)},
                        )
                row["elapsed_seconds"] = perf_counter() - started
            events = [e for e in capture.events if e.get("operation_id") == job_id]
            requests = [e for e in events if e.get("event") == "model.request_finished"]
            row["requests"] = len(requests)
            row["failed_requests"] = sum(r.get("status") == "failed" for r in requests)
            row["provider_retries"] = sum(r.get("attempt", 1) > 1 for r in requests)
            for key in (
                "input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "reasoning_tokens",
                "queue_wait_ms",
                "latency_ms",
            ):
                row[key] = sum(r.get(key, 0) for r in requests)
            row["stages"] = {
                stage: sum(r.get("stage") == stage for r in requests)
                for stage in sorted({r.get("stage", "unknown") for r in requests})
            }
            atomic_write_json(case / f"{args.engine}-{job_id}-metrics.json", row)
            atomic_write_json(case / f"{args.engine}-{job_id}-events.json", events)
            print(json.dumps(row), flush=True)
            return row

    results = await asyncio.gather(*(run_one(lecture) for lecture in args.lectures))
    atomic_write_json(output / f"{args.engine}-{uuid4().hex}-results.json", results)


if __name__ == "__main__":
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.local", override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--course", required=True)
    parser.add_argument("--lectures", nargs="+", required=True)
    parser.add_argument("--engine", choices=["baseline", "agent"], required=True)
    parser.add_argument("--language", default="en")
    os.environ.setdefault("LECTUREPILOT_LATEX_COMPILER_URL", "http://127.0.0.1:8081")
    os.environ.setdefault(
        "LECTUREPILOT_DOCUMENT_CONVERTER_URL", "http://127.0.0.1:8082"
    )
    asyncio.run(main(parser.parse_args()))
