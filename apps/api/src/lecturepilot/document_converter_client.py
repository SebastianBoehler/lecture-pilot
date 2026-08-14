from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZipFile

import httpx

from lecturepilot.source_normalization_models import NormalizedDocument
from lecturepilot.source_normalization_store import (
    SourceNormalizationError,
    load_normalized_document,
)


MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 1_000


class DocumentConverterError(RuntimeError):
    pass


class DocumentConverterClient:
    def __init__(self, base_url: str, *, transport: httpx.BaseTransport | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    def convert(
        self,
        *,
        path: Path,
        source_path: str,
        sha256: str,
        normalized_root: Path,
    ) -> NormalizedDocument:
        revision_root = normalized_root / sha256
        if revision_root.exists():
            return _load(revision_root=normalized_root, sha256=sha256)
        response = self._request(path=path, source_path=source_path, sha256=sha256)
        _store_archive(response.content, normalized_root=normalized_root, sha256=sha256)
        return _load(revision_root=normalized_root, sha256=sha256)

    def _request(self, *, path: Path, source_path: str, sha256: str) -> httpx.Response:
        try:
            with (
                path.open("rb") as source,
                httpx.Client(
                    transport=self.transport,
                    timeout=60,
                ) as client,
            ):
                response = client.post(
                    f"{self.base_url}/convert",
                    data={"source_path": source_path, "source_sha256": sha256},
                    files={"file": (path.name, source, "application/octet-stream")},
                )
        except (OSError, httpx.HTTPError) as exc:
            raise DocumentConverterError("Document converter is unavailable.") from exc
        if response.status_code != 200:
            raise DocumentConverterError("Document converter rejected the source material.")
        if response.headers.get("content-type", "").split(";", 1)[0] != "application/zip":
            raise DocumentConverterError("Document converter returned an invalid response type.")
        if len(response.content) > MAX_ARCHIVE_BYTES:
            raise DocumentConverterError("Document converter response exceeds the size limit.")
        return response


def _store_archive(content: bytes, *, normalized_root: Path, sha256: str) -> None:
    normalized_root.mkdir(parents=True, exist_ok=True)
    try:
        with ZipFile(BytesIO(content)) as archive:
            members = archive.infolist()
            _validate_members(members)
            with TemporaryDirectory(prefix=f".{sha256}-", dir=normalized_root) as temporary:
                staging = Path(temporary) / sha256
                staging.mkdir()
                for member in members:
                    target = staging.joinpath(*PurePosixPath(member.filename).parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(member))
                os.rename(staging, normalized_root / sha256)
    except (BadZipFile, OSError) as exc:
        raise DocumentConverterError("Document converter returned an invalid archive.") from exc


def _validate_members(members) -> None:
    if not members or len(members) > MAX_ARCHIVE_MEMBERS:
        raise DocumentConverterError("Document converter returned an invalid archive.")
    if sum(member.file_size for member in members) > MAX_ARCHIVE_BYTES:
        raise DocumentConverterError("Document converter archive exceeds the size limit.")
    for member in members:
        path = PurePosixPath(member.filename)
        allowed = member.filename in {"manifest.json", "content.md", "rendered.pdf"}
        allowed = allowed or bool(path.parts[:1] == ("assets",) and len(path.parts) > 1)
        if path.is_absolute() or ".." in path.parts or member.is_dir() or not allowed:
            raise DocumentConverterError("Document converter returned an unsafe archive member.")


def _load(*, revision_root: Path, sha256: str) -> NormalizedDocument:
    try:
        return load_normalized_document(revision_root, sha256)
    except SourceNormalizationError as exc:
        raise DocumentConverterError("Normalized document validation failed.") from exc
