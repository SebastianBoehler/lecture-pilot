from __future__ import annotations

import hashlib
import http.client
import json
import os
import tempfile
from pathlib import Path, PurePosixPath
from typing import BinaryIO
from urllib.parse import quote, urlsplit
from zipfile import ZIP_DEFLATED, ZipFile

from lecturepilot.metadata_events import current_correlation_id
from lecturepilot.source_index_models import IndexedSourceFile
from lecturepilot.storage_layout import safe_id


COMPILATION_PROTOCOL_VERSION = "tectonic-0.16.9-handout-v2-tlextras-2022.0r0"
COMPILER_INPUT_KINDS = {
    "code",
    "image",
    "json",
    "latex",
    "latex-support",
    "markdown",
    "pdf",
    "svg",
    "table",
    "text",
}
MAX_COMPILER_INPUT_BYTES = 256 * 1024 * 1024
MAX_COMPILED_PDF_BYTES = 64 * 1024 * 1024
MAX_COMPILED_PDF_PAGES = 1_000
REQUEST_TIMEOUT_SECONDS = 60


class LatexCompilationError(RuntimeError):
    """Raised when the isolated compiler cannot produce a safe PDF."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "compilation_error",
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.request_id = request_id


def compile_latex_deck(
    *,
    source_root: Path,
    inputs: list[IndexedSourceFile],
    source_path: str,
    output_root: Path,
    lecture_id: str,
) -> Path:
    inputs = _validated_inputs(inputs, source_path)
    fingerprint = _fingerprint(inputs, source_path)
    stem = safe_id(PurePosixPath(source_path).stem)
    output = (
        output_root
        / "compiled-latex"
        / safe_id(lecture_id)
        / fingerprint
        / f"{stem}-{fingerprint[:12]}.pdf"
    )
    if _valid_pdf_path(output):
        _verify_input_hashes(source_root, inputs)
        return output

    archive, archive_size = _build_archive(source_root, inputs)
    try:
        payload = _request_compilation(archive, archive_size, source_path)
    finally:
        archive.close()
    _validate_pdf(payload)
    _write_atomic(output, payload)
    return output


def _validated_inputs(
    compiler_inputs: list[IndexedSourceFile], source_path: str
) -> list[IndexedSourceFile]:
    inputs = sorted(
        (item for item in compiler_inputs if item.kind in COMPILER_INPUT_KINDS),
        key=lambda item: item.path,
    )
    main = next((item for item in inputs if item.path == source_path), None)
    if main is None or main.kind != "latex":
        raise LatexCompilationError("The scheduled LaTeX source is not available for compilation.")
    if sum(item.size_bytes for item in inputs) > MAX_COMPILER_INPUT_BYTES:
        raise LatexCompilationError("The LaTeX source bundle is too large to compile safely.")
    return inputs


def _fingerprint(inputs: list[IndexedSourceFile], source_path: str) -> str:
    digest = hashlib.sha256()
    digest.update(f"{COMPILATION_PROTOCOL_VERSION}\0{source_path}\0".encode())
    for item in inputs:
        digest.update(f"{item.path}\0{item.sha256}\0".encode())
    return digest.hexdigest()


def _build_archive(source_root: Path, inputs: list[IndexedSourceFile]) -> tuple[BinaryIO, int]:
    root = source_root.resolve(strict=True)
    archive = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
    actual_total = 0
    try:
        with ZipFile(archive, "w", compression=ZIP_DEFLATED, compresslevel=6) as bundle:
            for item in inputs:
                relative = _safe_relative_path(item.path)
                source = source_root / relative
                resolved = source.resolve(strict=True)
                if (
                    source.is_symlink()
                    or not resolved.is_relative_to(root)
                    or not resolved.is_file()
                ):
                    raise LatexCompilationError("The LaTeX source bundle contains an unsafe path.")
                digest = hashlib.sha256()
                copied = 0
                with (
                    resolved.open("rb") as input_file,
                    bundle.open(relative.as_posix(), "w", force_zip64=True) as output_file,
                ):
                    while chunk := input_file.read(1024 * 1024):
                        copied += len(chunk)
                        actual_total += len(chunk)
                        if copied > item.size_bytes or actual_total > MAX_COMPILER_INPUT_BYTES:
                            raise _source_changed_error()
                        digest.update(chunk)
                        output_file.write(chunk)
                if copied != item.size_bytes or digest.hexdigest() != item.sha256:
                    raise _source_changed_error()
        size = archive.tell()
        if size > MAX_COMPILER_INPUT_BYTES:
            raise LatexCompilationError("The LaTeX source archive is too large to compile safely.")
        archive.seek(0)
        return archive, size
    except BaseException:
        archive.close()
        raise


def _verify_input_hashes(source_root: Path, inputs: list[IndexedSourceFile]) -> None:
    root = source_root.resolve(strict=True)
    for item in inputs:
        relative = _safe_relative_path(item.path)
        source = source_root / relative
        resolved = source.resolve(strict=True)
        if source.is_symlink() or not resolved.is_relative_to(root) or not resolved.is_file():
            raise LatexCompilationError("The LaTeX source bundle contains an unsafe path.")
        digest = hashlib.sha256()
        size = 0
        with resolved.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                size += len(chunk)
                if size > item.size_bytes:
                    raise _source_changed_error()
                digest.update(chunk)
        if size != item.size_bytes or digest.hexdigest() != item.sha256:
            raise _source_changed_error()


def _source_changed_error() -> LatexCompilationError:
    return LatexCompilationError(
        "Course source changed during compilation. Refresh and try again.",
        code="source_changed",
    )


def _safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise LatexCompilationError("The LaTeX source bundle contains an unsafe path.")
    return path


def _request_compilation(archive: BinaryIO, size: int, main_path: str) -> bytes:
    configured = os.getenv("LECTUREPILOT_LATEX_COMPILER_URL", "").strip()
    if not configured:
        raise LatexCompilationError("The isolated LaTeX compiler service is not configured.")
    parsed = urlsplit(configured)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username:
        raise LatexCompilationError("The isolated LaTeX compiler service URL is invalid.")
    connection_type = (
        http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    )
    connection = connection_type(
        parsed.hostname,
        parsed.port,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    endpoint = f"{parsed.path.rstrip('/')}/compile?main_path={quote(main_path, safe='')}"
    try:
        connection.putrequest("POST", endpoint)
        connection.putheader("Content-Type", "application/zip")
        connection.putheader("Content-Length", str(size))
        if correlation_id := current_correlation_id():
            connection.putheader("X-Request-ID", correlation_id)
        connection.endheaders()
        while chunk := archive.read(1024 * 1024):
            connection.send(chunk)
        response = connection.getresponse()
        payload = response.read(MAX_COMPILED_PDF_BYTES + 1)
        if response.status != 200:
            code = _response_error_code(payload)
            raise LatexCompilationError(
                "The isolated LaTeX compiler rejected the source bundle.",
                code=code,
                request_id=response.getheader("X-Request-ID"),
            )
        return payload
    except LatexCompilationError:
        raise
    except (OSError, http.client.HTTPException) as exc:
        raise LatexCompilationError(
            "The isolated LaTeX compiler is unavailable.", code="compiler_unavailable"
        ) from exc
    finally:
        connection.close()


def _validate_pdf(payload: bytes) -> None:
    if len(payload) > MAX_COMPILED_PDF_BYTES or not payload.startswith(b"%PDF"):
        raise LatexCompilationError("The isolated LaTeX compiler did not return a valid PDF.")
    try:
        import fitz

        document = fitz.open(stream=payload, filetype="pdf")
        try:
            if not 1 <= len(document) <= MAX_COMPILED_PDF_PAGES:
                raise LatexCompilationError(
                    "The isolated LaTeX compiler returned an invalid page count."
                )
        finally:
            document.close()
    except LatexCompilationError:
        raise
    except Exception as exc:
        raise LatexCompilationError(
            "The isolated LaTeX compiler did not return a valid PDF."
        ) from exc


def _response_error_code(payload: bytes) -> str:
    try:
        parsed = json.loads(payload.decode("utf-8"))
        code = parsed["error"]["code"]
    except (KeyError, TypeError, ValueError, UnicodeDecodeError):
        return "compiler_rejected"
    return code if isinstance(code, str) and len(code) <= 80 else "compiler_rejected"


def _valid_pdf_path(path: Path) -> bool:
    if not path.exists() or path.stat().st_size > MAX_COMPILED_PDF_BYTES:
        return False
    try:
        _validate_pdf(path.read_bytes())
    except (OSError, LatexCompilationError):
        return False
    return True


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".compiled-", suffix=".pdf", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
