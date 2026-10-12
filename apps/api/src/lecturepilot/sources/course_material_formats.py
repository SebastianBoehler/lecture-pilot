from __future__ import annotations

from dataclasses import dataclass


MiB = 1024 * 1024


@dataclass(frozen=True)
class CourseMaterialFormat:
    kind: str
    max_bytes: int
    media_types: frozenset[str]
    content_family: str


def _format(
    kind: str,
    max_mib: int,
    media_types: set[str],
    content_family: str,
) -> CourseMaterialFormat:
    return CourseMaterialFormat(kind, max_mib * MiB, frozenset(media_types), content_family)


_LATEX = _format("latex", 10, {"application/x-tex", "text/x-tex", "text/plain"}, "text")
_LATEX_SUPPORT = _format("latex-support", 10, {"text/plain"}, "text")
_CODE = _format(
    "code",
    5,
    {
        "application/javascript",
        "application/sql",
        "text/css",
        "text/javascript",
        "text/plain",
        "text/x-c",
        "text/x-c++src",
        "text/x-java-source",
        "text/x-python",
        "text/x-r-source",
        "text/x-shellscript",
        "text/x-sql",
        "text/x-typescript",
    },
    "text",
)


COURSE_MATERIAL_FORMATS: dict[str, CourseMaterialFormat] = {
    ".tex": _LATEX,
    ".sty": _LATEX_SUPPORT,
    ".cls": _LATEX_SUPPORT,
    ".bib": _format("latex-support", 10, {"application/x-bibtex", "text/plain"}, "text"),
    ".bst": _format("latex-support", 10, {"application/x-bibtex-style", "text/plain"}, "text"),
    ".md": _format("markdown", 5, {"text/markdown", "text/plain"}, "text"),
    ".txt": _format("text", 2, {"text/plain"}, "text"),
    ".csv": _format("table", 5, {"text/csv", "application/csv", "text/plain"}, "text"),
    ".json": _format("json", 2, {"application/json", "text/json"}, "json"),
    ".yaml": _format("code", 5, {"application/yaml", "text/yaml", "text/plain"}, "text"),
    ".yml": _format("code", 5, {"application/yaml", "text/yaml", "text/plain"}, "text"),
    ".toml": _CODE,
    ".xml": _format("code", 5, {"application/xml", "text/xml", "text/plain"}, "text"),
    ".html": _format("code", 5, {"text/html", "text/plain"}, "text"),
    ".css": _format("code", 5, {"text/css", "text/plain"}, "text"),
    ".pdf": _format("pdf", 100, {"application/pdf"}, "pdf"),
    ".docx": _format(
        "document",
        100,
        {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        "ooxml-word",
    ),
    ".pptx": _format(
        "presentation",
        100,
        {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
        "ooxml-presentation",
    ),
    ".xlsx": _format(
        "spreadsheet",
        100,
        {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        "ooxml-spreadsheet",
    ),
    ".png": _format("image", 20, {"image/png"}, "png"),
    ".jpg": _format("image", 20, {"image/jpeg"}, "jpeg"),
    ".jpeg": _format("image", 20, {"image/jpeg"}, "jpeg"),
    ".webp": _format("image", 20, {"image/webp"}, "webp"),
    ".gif": _format("image", 20, {"image/gif"}, "gif"),
    ".svg": _format("svg", 2, {"image/svg+xml"}, "svg"),
    ".mp4": _format("video", 500, {"video/mp4"}, "mp4"),
    ".webm": _format("video", 500, {"video/webm"}, "matroska"),
    ".mov": _format("video", 500, {"video/quicktime"}, "mp4"),
    ".mkv": _format("video", 500, {"video/x-matroska"}, "matroska"),
    ".avi": _format("video", 500, {"video/x-msvideo"}, "avi"),
    ".ipynb": _format("notebook", 20, {"application/x-ipynb+json", "application/json"}, "json"),
}


for _suffix in {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".h",
    ".hpp",
    ".java",
    ".jl",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".m",
    ".mm",
    ".php",
    ".py",
    ".r",
    ".rb",
    ".rs",
    ".scala",
    ".sh",
    ".sql",
    ".swift",
    ".ts",
    ".tsx",
}:
    COURSE_MATERIAL_FORMATS[_suffix] = _CODE


SOURCE_SUFFIXES = {suffix: policy.kind for suffix, policy in COURSE_MATERIAL_FORMATS.items()}
COURSE_MATERIAL_UPLOADS = {
    suffix: (policy.kind, policy.max_bytes) for suffix, policy in COURSE_MATERIAL_FORMATS.items()
}


OOXML_REQUIRED_PARTS = {
    "ooxml-word": ("word/document.xml", "wordprocessingml.document.main+xml"),
    "ooxml-presentation": (
        "ppt/presentation.xml",
        "presentationml.presentation.main+xml",
    ),
    "ooxml-spreadsheet": ("xl/workbook.xml", "spreadsheetml.sheet.main+xml"),
}
