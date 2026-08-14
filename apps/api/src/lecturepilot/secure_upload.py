from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import secrets
import unicodedata
from zipfile import BadZipFile, LargeZipFile, ZipFile

from fastapi import UploadFile

from lecturepilot.durable_files import ensure_durable_directory, fsync_directory
from lecturepilot.course_material_formats import (
    COURSE_MATERIAL_FORMATS,
    OOXML_REQUIRED_PARTS,
)
from lecturepilot.workspace import WorkspacePolicy, WorkspacePolicyError
from lecturepilot.workspace_capability import CapabilityRoot, WorkspaceCapability
from lecturepilot.workspace_fs import WorkspaceFS, WorkspaceFSError


@dataclass(frozen=True)
class StoredUpload:
    path: str
    kind: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class StagedCourseUpload:
    relative_path: PurePosixPath
    quarantine_path: Path
    kind: str
    size_bytes: int
    sha256: str

    def discard(self) -> None:
        self.quarantine_path.unlink(missing_ok=True)


async def store_course_upload(
    upload: UploadFile,
    *,
    uploads_root: Path,
    tenant_id: str,
    requested_path: str,
) -> StoredUpload:
    staged = await stage_course_upload(
        upload,
        quarantine_root=uploads_root / ".quarantine",
        tenant_id=tenant_id,
        requested_path=requested_path,
    )
    return promote_course_upload(staged, uploads_root=uploads_root)


async def stage_course_upload(
    upload: UploadFile,
    *,
    quarantine_root: Path,
    tenant_id: str,
    requested_path: str,
) -> StagedCourseUpload:
    requested_path = unicodedata.normalize("NFC", requested_path)
    policy = WorkspacePolicy()
    checked = policy.validate_course_material_upload(
        tenant_id=tenant_id,
        path=requested_path,
        size_bytes=0,
    )
    relative = PurePosixPath(requested_path)
    ensure_durable_directory(quarantine_root)
    quarantine_path = quarantine_root / f"{secrets.token_hex(16)}.part"
    size = 0
    digest = hashlib.sha256()
    header = bytearray()
    try:
        try:
            with quarantine_path.open("xb") as handle:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > checked.max_bytes:
                        raise WorkspacePolicyError(
                            f"{relative.suffix.lower()} files are limited to {checked.max_bytes} bytes."
                        )
                    if len(header) < 8192:
                        header.extend(chunk[: 8192 - len(header)])
                    digest.update(chunk)
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            _validate_content(
                relative.suffix.lower(),
                bytes(header),
                upload.content_type,
                staged_path=quarantine_path,
            )
        finally:
            await upload.close()
        return StagedCourseUpload(
            relative_path=relative,
            quarantine_path=quarantine_path,
            kind=checked.kind,
            size_bytes=size,
            sha256=digest.hexdigest(),
        )
    except BaseException:
        quarantine_path.unlink(missing_ok=True)
        raise


def promote_course_upload(staged: StagedCourseUpload, *, uploads_root: Path) -> StoredUpload:
    ensure_durable_directory(uploads_root)
    try:
        try:
            target = _promote_upload(
                uploads_root,
                staged.relative_path,
                staged.quarantine_path,
            )
        except WorkspaceFSError as exc:
            raise WorkspacePolicyError("Course material path is not safe.") from exc
        return StoredUpload(
            path=target.relative_to(uploads_root).as_posix(),
            kind=staged.kind,
            size_bytes=staged.size_bytes,
            sha256=staged.sha256,
        )
    finally:
        staged.discard()


def _promote_upload(root: Path, relative: PurePosixPath, source: Path) -> Path:
    workspace = WorkspaceFS(WorkspaceCapability((CapabilityRoot("/uploads", root, writable=True),)))
    logical = f"/uploads/{relative.as_posix()}"
    resolved = workspace.resolve(logical, for_write=True)
    ensure_durable_directory(resolved.path.parent)
    resolved = workspace.resolve(logical, for_write=True)
    if resolved.path.exists():
        raise WorkspacePolicyError("A course material file already exists at this path.")
    try:
        # Quarantine and course uploads share the course filesystem. A rename keeps
        # exactly one directory entry at every crash point, unlike link-then-unlink.
        os.rename(source, resolved.path)
        fsync_directory(resolved.path.parent)
        fsync_directory(source.parent)
    except (FileExistsError, OSError) as exc:
        raise WorkspacePolicyError("Course material could not be safely promoted.") from exc
    return resolved.path


def _validate_content(
    suffix: str,
    header: bytes,
    declared_type: str | None,
    *,
    staged_path: Path | None = None,
) -> None:
    if not header:
        raise WorkspacePolicyError("Empty course material files are not accepted.")
    checked_content = staged_path.read_bytes() if suffix == ".svg" and staged_path else header
    lowered = checked_content.lower().lstrip()
    valid = _matches_signature(suffix, header, lowered, staged_path=staged_path)
    if not valid:
        raise WorkspacePolicyError("File contents do not match the requested file type.")
    allowed_types = COURSE_MATERIAL_FORMATS[suffix].media_types
    declared = (declared_type or "").split(";", 1)[0].strip().lower()
    if declared and declared != "application/octet-stream" and declared not in allowed_types:
        raise WorkspacePolicyError("Declared media type does not match the requested file type.")


def _matches_signature(
    suffix: str,
    header: bytes,
    lowered: bytes,
    *,
    staged_path: Path | None,
) -> bool:
    family = COURSE_MATERIAL_FORMATS[suffix].content_family
    if family == "pdf":
        return header.startswith(b"%PDF-")
    if family == "png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if family == "jpeg":
        return header.startswith(b"\xff\xd8\xff")
    if family == "gif":
        return header.startswith((b"GIF87a", b"GIF89a"))
    if family == "webp":
        return header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    if family == "matroska":
        return header.startswith(b"\x1aE\xdf\xa3")
    if family == "avi":
        return header.startswith(b"RIFF") and header[8:12] == b"AVI "
    if family == "mp4":
        return len(header) >= 12 and header[4:8] == b"ftyp"
    if family == "svg":
        forbidden = (b"<script", b"<!doctype", b"<!entity", b"javascript:", b"http://", b"https://")
        return b"<svg" in lowered[:2048] and not any(value in lowered for value in forbidden)
    if family == "json":
        return lowered.startswith((b"{", b"[")) and b"\x00" not in header
    if family == "text":
        return _looks_like_text(header)
    if family in OOXML_REQUIRED_PARTS and staged_path:
        return _matches_ooxml(staged_path, family=family)
    return False


def _matches_ooxml(path: Path, *, family: str) -> bool:
    required_part, required_type = OOXML_REQUIRED_PARTS[family]
    try:
        with ZipFile(path) as archive:
            members = archive.infolist()
            names = {item.filename for item in members}
            if (
                len(members) > 10_000
                or "[Content_Types].xml" not in names
                or required_part not in names
                or any(item.flag_bits & 1 for item in members)
                or any("vbaproject.bin" in item.filename.lower() for item in members)
            ):
                return False
            content_types_info = archive.getinfo("[Content_Types].xml")
            if content_types_info.file_size > 1024 * 1024:
                return False
            content_types = archive.read(content_types_info).lower()
    except (BadZipFile, LargeZipFile, KeyError, OSError):
        return False
    return required_type.encode() in content_types and b"macroenabled" not in content_types


def _looks_like_text(header: bytes) -> bool:
    if b"\x00" in header:
        return False
    allowed_controls = {9, 10, 13}
    controls = sum(byte < 32 and byte not in allowed_controls or byte == 127 for byte in header)
    return controls / len(header) <= 0.01
