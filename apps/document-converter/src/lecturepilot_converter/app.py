from __future__ import annotations

from hashlib import sha256
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Annotated
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from lecturepilot_converter.conversion import (
    MEDIA_TYPES,
    DocumentConversionError,
    convert_document,
)
from lecturepilot_converter.office_render import OfficeRenderError
from lecturepilot_converter.office_xlsx import SpreadsheetConversionError


MAX_DOCUMENT_BYTES = 100 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024

app = FastAPI(title="LecturePilot document converter")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/convert", response_class=FileResponse)
async def convert(
    file: Annotated[UploadFile, File()],
    source_path: Annotated[str, Form(min_length=1, max_length=500)],
    source_sha256: Annotated[str, Form(pattern=r"^[0-9a-f]{64}$")],
):
    relative = _validated_source_path(source_path)
    temporary = TemporaryDirectory(prefix="lecturepilot-document-")
    temporary_root = Path(temporary.name)
    try:
        source = temporary_root / f"source{relative.suffix.lower()}"
        actual_sha256 = await _store_upload(file, source)
        if actual_sha256 != source_sha256:
            raise HTTPException(
                status_code=400,
                detail="Uploaded document does not match its source revision.",
            )
        normalized_root = temporary_root / "normalized"
        try:
            await run_in_threadpool(
                convert_document,
                source,
                source_path=source_path,
                source_sha256=source_sha256,
                output_root=normalized_root,
            )
        except (DocumentConversionError, OfficeRenderError, SpreadsheetConversionError) as exc:
            raise HTTPException(
                status_code=422,
                detail="Document contents could not be converted safely.",
            ) from exc
        archive_path = temporary_root / "normalized.zip"
        await run_in_threadpool(
            _archive_revision,
            normalized_root / source_sha256,
            archive_path,
        )
        return FileResponse(
            archive_path,
            media_type="application/zip",
            filename="normalized.zip",
            background=BackgroundTask(temporary.cleanup),
        )
    except BaseException:
        temporary.cleanup()
        raise


def _validated_source_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or any(part.startswith(".") for part in path.parts):
        raise HTTPException(status_code=400, detail="Document path is not accepted.")
    if path.suffix.lower() not in MEDIA_TYPES:
        raise HTTPException(status_code=400, detail="Document format is not accepted.")
    return path


async def _store_upload(upload: UploadFile, target: Path) -> str:
    digest = sha256()
    size = 0
    try:
        with target.open("xb") as handle:
            while chunk := await upload.read(CHUNK_BYTES):
                size += len(chunk)
                if size > MAX_DOCUMENT_BYTES:
                    raise HTTPException(status_code=413, detail="Document exceeds the size limit.")
                digest.update(chunk)
                handle.write(chunk)
    finally:
        await upload.close()
    return digest.hexdigest()


def _archive_revision(revision_root: Path, archive_path: Path) -> None:
    with ZipFile(archive_path, "x", compression=ZIP_DEFLATED) as archive:
        for path in sorted(item for item in revision_root.rglob("*") if item.is_file()):
            archive.write(path, path.relative_to(revision_root).as_posix())
