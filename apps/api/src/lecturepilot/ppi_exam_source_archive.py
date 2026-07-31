from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path, PurePosixPath
import shutil
import stat
from zipfile import BadZipFile, ZipFile, ZipInfo

import fitz

from lecturepilot.ppi_exam_source_models import NormalizedPpiFile


DEFAULT_MAX_FILES = 80
DEFAULT_MAX_COMPRESSED_BYTES = 30 * 1024 * 1024
DEFAULT_MAX_EXPANDED_BYTES = 120 * 1024 * 1024


class PpiArchiveError(ValueError):
    """Raised when a PPI download cannot be safely normalized."""


def normalize_ppi_archive(
    archive: bytes,
    *,
    output_root: Path,
    max_files: int = DEFAULT_MAX_FILES,
    max_compressed_bytes: int = DEFAULT_MAX_COMPRESSED_BYTES,
    max_expanded_bytes: int = DEFAULT_MAX_EXPANDED_BYTES,
) -> list[NormalizedPpiFile]:
    if len(archive) > max_compressed_bytes:
        raise PpiArchiveError("PPI archive exceeds the compressed size limit.")
    try:
        with ZipFile(BytesIO(archive)) as bundle:
            members = [item for item in bundle.infolist() if not item.is_dir()]
            _validate_members(
                members,
                max_files=max_files,
                max_compressed_bytes=max_compressed_bytes,
                max_expanded_bytes=max_expanded_bytes,
            )
            normalized = [
                _normalize_member(bundle, item, index) for index, item in enumerate(members)
            ]
    except BadZipFile as exc:
        raise PpiArchiveError("PPI download is not a valid ZIP archive.") from exc

    output_root.mkdir(parents=True, exist_ok=True)
    try:
        results = []
        for metadata, text in normalized:
            target = output_root / metadata.text_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            results.append(metadata)
        return results
    except BaseException:
        _clear_directory(output_root)
        raise


def _validate_members(
    members: list[ZipInfo],
    *,
    max_files: int,
    max_compressed_bytes: int,
    max_expanded_bytes: int,
) -> None:
    if not members:
        raise PpiArchiveError("PPI archive contains no protocol files.")
    if len(members) > max_files:
        raise PpiArchiveError("PPI archive contains too many files.")
    if sum(item.compress_size for item in members) > max_compressed_bytes:
        raise PpiArchiveError("PPI archive exceeds the compressed size limit.")
    if sum(item.file_size for item in members) > max_expanded_bytes:
        raise PpiArchiveError("PPI archive exceeds the expanded size limit.")
    seen: set[str] = set()
    for item in members:
        path = _safe_member_path(item.filename)
        key = path.as_posix().casefold()
        if key in seen:
            raise PpiArchiveError("PPI archive contains a duplicate path.")
        seen.add(key)
        if stat.S_ISLNK(item.external_attr >> 16):
            raise PpiArchiveError("PPI archive contains a symbolic link.")
        if path.suffix.casefold() not in {".pdf", ".txt", ".md"}:
            raise PpiArchiveError("PPI archive contains an unsupported file type.")


def _safe_member_path(name: str) -> PurePosixPath:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or not path.parts or ".." in path.parts or ":" in path.parts[0]:
        raise PpiArchiveError("PPI archive contains an unsafe path.")
    if any(part in {"", "."} or part.startswith(".") for part in path.parts):
        raise PpiArchiveError("PPI archive contains a hidden path.")
    return path


def _normalize_member(bundle: ZipFile, item: ZipInfo, index: int) -> tuple[NormalizedPpiFile, str]:
    path = _safe_member_path(item.filename)
    content = bundle.read(item)
    if len(content) != item.file_size:
        raise PpiArchiveError("PPI archive member size changed during extraction.")
    if path.suffix.casefold() == ".pdf":
        text = _pdf_text(content)
        media_type = "application/pdf"
    else:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise PpiArchiveError("PPI text protocol is not valid UTF-8.") from exc
        media_type = "text/markdown" if path.suffix.casefold() == ".md" else "text/plain"
    text_path = f"normalized/{index + 1:03d}-{path.stem[:100]}.txt"
    return (
        NormalizedPpiFile(
            path=path.as_posix(),
            text_path=text_path,
            media_type=media_type,
            sha256=sha256(content).hexdigest(),
            size_bytes=len(content),
            character_count=len(text),
        ),
        text,
    )


def _pdf_text(content: bytes) -> str:
    try:
        document = fitz.open(stream=content, filetype="pdf")
        if document.page_count < 1:
            raise PpiArchiveError("PPI archive contains an invalid PDF.")
        text = "\n\n".join(page.get_text("text") for page in document)
        document.close()
        return text
    except PpiArchiveError:
        raise
    except Exception as exc:
        raise PpiArchiveError("PPI archive contains an invalid PDF.") from exc


def _clear_directory(path: Path) -> None:
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
