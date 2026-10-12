"""The converter runs only under the Compose "authoring" profile; when stopped, fail clearly."""

from pathlib import Path
from types import SimpleNamespace
from typing import NoReturn

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import httpx
import pytest

from lecturepilot.app_exception_handlers import register_exception_handlers
from lecturepilot.course_canvas_generation_http import run_canvas_generation_request
from lecturepilot.course_canvas_generation_jobs import CanvasGenerationStore
from lecturepilot.document_converter_client import (
    DocumentConverterClient,
    DocumentConverterUnavailable,
)
from lecturepilot.pdf_page_ocr import PdfPageRecord, page_text
from lecturepilot.storage_layout import StorageLayout
from lecturepilot.tenancy import TenantContext


def _unreachable(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("Name or service not known", request=request)


def test_unreachable_converter_raises_an_actionable_unavailable_error(tmp_path: Path) -> None:
    source = tmp_path / "reader.docx"
    source.write_bytes(b"office document")
    client = DocumentConverterClient(
        "http://document-converter:8080", transport=httpx.MockTransport(_unreachable)
    )

    with pytest.raises(DocumentConverterUnavailable, match="--profile authoring"):
        client.convert(
            path=source,
            source_path="reader.docx",
            sha256="a" * 64,
            normalized_root=tmp_path / "normalized",
        )


def test_pdf_ocr_does_not_silently_drop_pages_when_the_converter_is_stopped(monkeypatch):
    monkeypatch.setenv("LECTUREPILOT_DOCUMENT_CONVERTER_URL", "http://document-converter:8080")

    def unavailable(_self, **_request):
        raise DocumentConverterUnavailable()

    monkeypatch.setattr(DocumentConverterClient, "ocr_page", unavailable)
    record = PdfPageRecord(
        number=1, native_text="", links=(), raster_ratio=1.0, width=1, height=1, image=b"png"
    )

    with pytest.raises(DocumentConverterUnavailable):
        page_text(record, None)


def test_routes_answer_503_with_the_operator_action() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/convert", response_model=None)
    def convert() -> NoReturn:
        raise DocumentConverterUnavailable()

    response = TestClient(app).post("/convert")

    assert response.status_code == 503
    assert "docker compose --profile authoring up -d" in response.json()["detail"]


@pytest.mark.asyncio
async def test_canvas_generation_reports_a_stopped_converter_as_503(tmp_path) -> None:
    store = CanvasGenerationStore(StorageLayout(tmp_path), lease_seconds=45)

    async def generate(_generation_id: str, _attempt: int) -> NoReturn:
        raise DocumentConverterUnavailable()

    with pytest.raises(HTTPException) as caught:
        await run_canvas_generation_request(
            app=SimpleNamespace(state=SimpleNamespace()),
            store=store,
            course_id="course-1",
            lecture_id="lecture-01",
            context=TenantContext(tenant_id="tenant-1", user_id="professor-1", roles=frozenset()),
            request_key="request-key-converter-01",
            generate=generate,
        )

    assert caught.value.status_code == 503
    assert "--profile authoring" in caught.value.detail
    assert caught.value.headers["X-Generation-Error-Code"] == "document_converter_unavailable"
