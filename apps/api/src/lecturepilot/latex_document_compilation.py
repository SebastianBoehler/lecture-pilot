from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile


MAX_TRUSTED_TEX_BYTES = 2 * 1024 * 1024
DOCUMENT_PROTOCOL_VERSION = "practice-exam-document-v1"


def compile_latex_document(*, source: str, output: Path) -> Path:
    from lecturepilot import latex_compilation_client as compiler

    payload = source.encode("utf-8")
    if not payload or len(payload) > MAX_TRUSTED_TEX_BYTES:
        raise compiler.LatexCompilationError("The trusted LaTeX document is too large.")
    fingerprint = sha256(DOCUMENT_PROTOCOL_VERSION.encode() + b"\0" + payload).hexdigest()
    fingerprint_path = output.with_suffix(output.suffix + ".sha256")
    if (
        fingerprint_path.is_file()
        and fingerprint_path.read_text(encoding="ascii") == fingerprint
        and compiler._valid_pdf_path(output)
    ):
        return output
    archive = tempfile.SpooledTemporaryFile(max_size=2 * 1024 * 1024, mode="w+b")
    try:
        with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
            bundle.writestr("document.tex", payload)
        archive_size = archive.tell()
        archive.seek(0)
        pdf = compiler._request_compilation(archive, archive_size, "document.tex")
    finally:
        archive.close()
    compiler._validate_pdf(pdf)
    compiler._write_atomic(output, pdf)
    compiler._write_atomic(fingerprint_path, fingerprint.encode("ascii"))
    return output
