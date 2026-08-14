from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from lecturepilot.course_builder_source import course_builder_source_document
from test_course_source_partitioning import (
    _client,
    _confirm_routing,
    _create_full_course,
    _pdf,
    _upload,
)


def test_powerpoint_flows_from_upload_through_routing_to_canvas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path)
    path = "Lecture01.pptx"
    _create_full_course(client, (path,))
    _upload(client, path, _minimal_pptx())
    monkeypatch.setenv("LECTUREPILOT_DOCUMENT_CONVERTER_URL", "http://converter:8080")

    def convert(_self, **kwargs):
        revision = kwargs["normalized_root"] / kwargs["sha256"]
        revision.mkdir(parents=True, exist_ok=True)
        (revision / "manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "source_path": kwargs["source_path"],
                    "source_sha256": kwargs["sha256"],
                    "media_type": (
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    ),
                    "blocks": [
                        {
                            "kind": "heading",
                            "text": "Native PowerPoint evidence",
                            "locator": {"slide": 1},
                            "extraction": "native",
                        }
                    ],
                    "warnings": [],
                }
            ),
            encoding="utf-8",
        )
        (revision / "rendered.pdf").write_bytes(_pdf("Rendered PowerPoint slide"))

    monkeypatch.setattr(
        "lecturepilot.source_document_normalization.DocumentConverterClient.convert",
        convert,
    )
    _confirm_routing(client)

    document = course_builder_source_document(client.app, "partitioned-course", "lecture-01")

    assert document.source_ref == path
    assert document.sections[0].source_ref == f"{path} slide 1"
    assert any(
        block.text == "Native PowerPoint evidence"
        for section in document.sections
        for block in section.blocks
    )
    assert any(
        block.caption == f"Original slide 1 from {path}"
        for section in document.sections
        for block in section.blocks
    )


def _minimal_pptx() -> bytes:
    payload = BytesIO()
    with ZipFile(payload, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Override PartName="/ppt/presentation.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.presentationml.'
                'presentation.main+xml"/>'
                "</Types>"
            ),
        )
        archive.writestr("ppt/presentation.xml", "<presentation/>")
    return payload.getvalue()
