from pathlib import Path

import pytest

from lecturepilot.document_converter_client import DocumentConverterError
from lecturepilot.source_bundle import SourceBundleFile
from lecturepilot.source_document_normalization import normalize_selected_documents


def test_normalizes_only_native_office_sources_by_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    uploads = tmp_path / "uploads"
    normalized = tmp_path / "normalized"
    presentation = uploads / "slides" / "lecture.pptx"
    presentation.parent.mkdir(parents=True)
    presentation.write_bytes(b"presentation")
    notes = uploads / "notes.md"
    notes.write_text("# Notes", encoding="utf-8")
    calls = []

    def convert(self, **kwargs):
        calls.append(kwargs)

    monkeypatch.setenv("LECTUREPILOT_DOCUMENT_CONVERTER_URL", "http://converter:8080")
    monkeypatch.setattr(
        "lecturepilot.source_document_normalization.DocumentConverterClient.convert", convert
    )

    normalize_selected_documents(
        files=[
            SourceBundleFile(
                path="slides/lecture.pptx",
                kind="presentation",
                size_bytes=12,
                sha256="a" * 64,
            ),
            SourceBundleFile(
                path="notes.md",
                kind="markdown",
                size_bytes=7,
                sha256="b" * 64,
            ),
        ],
        source_root=uploads,
        normalized_root=normalized,
    )

    assert calls == [
        {
            "path": presentation,
            "source_path": "slides/lecture.pptx",
            "sha256": "a" * 64,
            "normalized_root": normalized,
        }
    ]


def test_office_source_requires_configured_converter(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("LECTUREPILOT_DOCUMENT_CONVERTER_URL", raising=False)

    with pytest.raises(DocumentConverterError, match="not configured"):
        normalize_selected_documents(
            files=[
                SourceBundleFile(
                    path="reader.docx",
                    kind="document",
                    size_bytes=12,
                    sha256="a" * 64,
                )
            ],
            source_root=tmp_path,
            normalized_root=tmp_path / "normalized",
        )
