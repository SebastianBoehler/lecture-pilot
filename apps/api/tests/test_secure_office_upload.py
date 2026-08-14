from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest

from auth_helpers import professor_headers
from test_secure_upload import _client


@pytest.mark.parametrize(
    ("path", "kind", "media_type", "part", "content_type"),
    [
        (
            "notes/reader.docx",
            "document",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "word/document.xml",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
        ),
        (
            "slides/lecture.pptx",
            "presentation",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "ppt/presentation.xml",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml",
        ),
        (
            "data/results.xlsx",
            "spreadsheet",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xl/workbook.xml",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
        ),
    ],
)
def test_upload_accepts_macro_free_ooxml_documents(
    tmp_path: Path,
    path: str,
    kind: str,
    media_type: str,
    part: str,
    content_type: str,
) -> None:
    client = _client(tmp_path)
    payload = _ooxml(part=part, content_type=content_type)

    response = client.post(
        "/admin/courses/martius-ml/materials",
        headers=professor_headers(),
        data={"path": path},
        files={"file": (Path(path).name, payload, media_type)},
    )

    assert response.status_code == 200
    assert response.json()["kind"] == kind


def test_upload_rejects_generic_zip_disguised_as_powerpoint(tmp_path: Path) -> None:
    client = _client(tmp_path)
    payload = BytesIO()
    with ZipFile(payload, "w") as archive:
        archive.writestr("notes.txt", "not a presentation")

    response = client.post(
        "/admin/courses/martius-ml/materials",
        headers=professor_headers(),
        data={"path": "slides/fake.pptx"},
        files={"file": ("fake.pptx", payload.getvalue(), "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "File contents do not match the requested file type."


def test_upload_rejects_macro_payload_inside_xlsx_container(tmp_path: Path) -> None:
    client = _client(tmp_path)
    payload = _ooxml(
        part="xl/workbook.xml",
        content_type=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"),
        extra_part="xl/vbaProject.bin",
    )

    response = client.post(
        "/admin/courses/martius-ml/materials",
        headers=professor_headers(),
        data={"path": "data/unsafe.xlsx"},
        files={"file": ("unsafe.xlsx", payload, "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "File contents do not match the requested file type."


def _ooxml(*, part: str, content_type: str, extra_part: str | None = None) -> bytes:
    payload = BytesIO()
    with ZipFile(payload, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                f'<Override PartName="/{part}" ContentType="{content_type}"/>'
                "</Types>"
            ),
        )
        archive.writestr(part, "<root/>")
        if extra_part:
            archive.writestr(extra_part, b"macro")
    return payload.getvalue()
