from __future__ import annotations


class CompilerServiceError(RuntimeError):
    def __init__(self, code: str, message: str, *, status: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


INVALID_REQUEST = "Invalid compilation request."
INVALID_ARCHIVE = "The source archive is invalid."
ARCHIVE_LIMIT = "The source archive exceeds compilation limits."
MAIN_UNAVAILABLE = "The selected LaTeX document is unavailable."
COMPILE_FAILED = "LaTeX slide rendering failed. Upload a matching PDF or fix the source dependencies."
COMPILE_TIMEOUT = (
    "LaTeX slide rendering timed out. Upload a matching PDF or simplify the source."
)
INVALID_OUTPUT = "LaTeX did not produce a valid PDF."
