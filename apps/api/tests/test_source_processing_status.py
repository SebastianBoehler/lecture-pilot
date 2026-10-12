from lecturepilot.sources import source_processing_status
from lecturepilot.sources.course_source_routing_models import (
    CourseSourceRoutingManifest,
    SourceProcessingStatus,
)


def _manifest(sha: str) -> CourseSourceRoutingManifest:
    return CourseSourceRoutingManifest.model_validate(
        {
            "course_id": "course",
            "source_revision": "a" * 64,
            "confirmed": False,
            "routes": [
                {
                    "path": "slides.pdf",
                    "kind": "pdf",
                    "sha256": sha,
                    "role": "lecture",
                    "lecture_id": "lecture-01",
                }
            ],
        }
    )


def test_pdf_ocr_triage_is_computed_once_per_file_content(tmp_path, monkeypatch) -> None:
    calls = []

    def triage(path: str) -> bool:
        calls.append(path)
        return True

    monkeypatch.setattr(source_processing_status, "pdf_requires_ocr", triage)
    roots = {"source_root": tmp_path / "uploads", "normalized_root": tmp_path / "normalized"}

    first = source_processing_status.with_processing_status(_manifest("b" * 64), **roots)
    again = source_processing_status.with_processing_status(_manifest("b" * 64), **roots)
    changed = source_processing_status.with_processing_status(_manifest("c" * 64), **roots)

    assert first.routes[0].processing_status is SourceProcessingStatus.OCR_NEEDED
    assert again.routes[0].processing_status is SourceProcessingStatus.OCR_NEEDED
    assert changed.routes[0].processing_status is SourceProcessingStatus.OCR_NEEDED
    assert len(calls) == 2  # Once per distinct file content, not once per request.
