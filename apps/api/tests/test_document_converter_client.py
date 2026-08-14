from io import BytesIO
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
import pytest

from lecturepilot.document_converter_client import (
    DocumentConverterClient,
    DocumentConverterError,
)


SOURCE_SHA256 = "a" * 64


def test_converter_client_validates_and_stores_revision_archive(tmp_path: Path) -> None:
    archive = _archive(
        {
            "manifest.json": json.dumps(_manifest()),
            "content.md": "## Course overview",
            "assets/slide-001.png": b"slide",
        }
    )
    client = _client(archive)
    source = tmp_path / "overview.docx"
    source.write_bytes(b"office document")

    document = client.convert(
        path=source,
        source_path="week-01/overview.docx",
        sha256=SOURCE_SHA256,
        normalized_root=tmp_path / "normalized",
    )

    revision = tmp_path / "normalized" / SOURCE_SHA256
    assert document.source_sha256 == SOURCE_SHA256
    assert (revision / "content.md").read_text(encoding="utf-8") == "## Course overview"
    assert (revision / "assets" / "slide-001.png").read_bytes() == b"slide"


def test_converter_client_rejects_traversing_archive_member(tmp_path: Path) -> None:
    client = _client(_archive({"manifest.json": json.dumps(_manifest()), "../escape": b"bad"}))
    source = tmp_path / "overview.docx"
    source.write_bytes(b"office document")

    with pytest.raises(DocumentConverterError, match="unsafe archive member"):
        client.convert(
            path=source,
            source_path="week-01/overview.docx",
            sha256=SOURCE_SHA256,
            normalized_root=tmp_path / "normalized",
        )

    assert not (tmp_path / "escape").exists()


def test_ocr_page_returns_source_located_ocr_text() -> None:
    def response(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/ocr-page"
        return httpx.Response(
            200,
            json={
                "required": True,
                "extraction": "ocr",
                "text": "Bayes-Regel aus dem Scan",
                "warning": None,
                "locator": {"page": 3, "bbox": [0, 0, 1024, 768]},
            },
        )

    result = DocumentConverterClient(
        "http://converter:8080",
        transport=httpx.MockTransport(response),
    ).ocr_page(
        image=b"\x89PNG\r\n\x1a\nscan",
        native_text="",
        raster_ratio=1.0,
        page=3,
        width=1024,
        height=768,
    )

    assert result.extraction == "ocr"
    assert result.locator.page == 3
    assert result.text == "Bayes-Regel aus dem Scan"


def _client(archive: bytes) -> DocumentConverterClient:
    def response(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=archive, headers={"content-type": "application/zip"})

    return DocumentConverterClient(
        "http://converter:8080",
        transport=httpx.MockTransport(response),
    )


def _archive(files: dict[str, str | bytes]) -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


def _manifest() -> dict:
    return {
        "schema_version": 1,
        "source_path": "week-01/overview.docx",
        "source_sha256": SOURCE_SHA256,
        "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "blocks": [
            {
                "kind": "image",
                "asset_path": "assets/slide-001.png",
                "locator": {"page": 1},
                "extraction": "rendered",
            }
        ],
        "warnings": [],
    }
