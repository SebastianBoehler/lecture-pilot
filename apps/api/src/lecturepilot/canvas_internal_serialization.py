from __future__ import annotations

from typing import Protocol

from lecturepilot.canvas_models import CanvasDocument, CanvasSection


class _RepairTarget(Protocol):
    candidate: CanvasDocument

    def model_dump(self, *, mode: str) -> dict: ...


class _GenerationJob(Protocol):
    canvas: CanvasDocument | None
    repair: _RepairTarget | None

    def model_dump(self, *, mode: str) -> dict: ...


def canvas_section_internal_payload(section: CanvasSection) -> dict:
    payload = section.model_dump(mode="json")
    if section.source_section_id is not None:
        payload["source_section_id"] = section.source_section_id
    return payload


def canvas_document_internal_payload(document: CanvasDocument) -> dict:
    payload = document.model_dump(mode="json")
    payload["sections"] = [
        canvas_section_internal_payload(section) for section in document.sections
    ]
    return payload


def canvas_generation_job_internal_payload(job: _GenerationJob) -> dict:
    payload = job.model_dump(mode="json")
    if job.canvas is not None:
        payload["canvas"] = canvas_document_internal_payload(job.canvas)
    if job.repair is not None:
        repair = job.repair.model_dump(mode="json")
        repair["candidate"] = canvas_document_internal_payload(job.repair.candidate)
        payload["repair"] = repair
    return payload
