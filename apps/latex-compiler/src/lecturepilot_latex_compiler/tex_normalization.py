from __future__ import annotations

from pathlib import Path
import re


_TEX_SOURCE_SUFFIXES = {".cls", ".sty", ".tex"}
_OPTIONAL_PACKAGE_REPLACEMENTS = {
    b"dsfont": rb"\providecommand{\mathds}[1]{\mathbf{#1}}",
    b"epsdice": rb"\providecommand{\epsdice}[1]{#1}",
    b"ulem": (
        rb"\providecommand{\sout}[1]{#1}"
        b"\n"
        rb"\providecommand{\uline}[1]{\underline{#1}}"
    ),
}
_OPTIONAL_PACKAGE = re.compile(
    rb"\\(?:usepackage|RequirePackage)(?:\[[^\]\r\n]*\])?"
    rb"\{(dsfont|epsdice|ulem)\}"
)
_INPUT_ENCODING = re.compile(
    rb"\\usepackage\[(?P<encoding>latin1|latin-1|iso-8859-1|ansinew|cp1252)\]"
    rb"\{inputenc\}",
    re.IGNORECASE,
)


def replace_optional_visual_dependencies(source_root: Path) -> None:
    for path in source_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _TEX_SOURCE_SUFFIXES:
            continue
        content = path.read_bytes()
        normalized = _OPTIONAL_PACKAGE.sub(_replace_optional_package, content)
        if normalized != content:
            path.write_bytes(normalized)


def normalize_legacy_input_encodings(source_root: Path) -> None:
    for path in source_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _TEX_SOURCE_SUFFIXES:
            continue
        content = path.read_bytes()
        match = _INPUT_ENCODING.search(content)
        if match is None:
            continue
        try:
            normalized = content.decode("utf-8")
        except UnicodeDecodeError:
            encoding = match.group("encoding").decode("ascii").lower()
            codec = "cp1252" if encoding in {"ansinew", "cp1252"} else "latin-1"
            normalized = content.decode(codec)
        normalized = _INPUT_ENCODING.sub(
            rb"\\usepackage[utf8]{inputenc}", normalized.encode("utf-8")
        ).decode("utf-8")
        path.write_text(normalized, encoding="utf-8")


def _replace_optional_package(match: re.Match[bytes]) -> bytes:
    return _OPTIONAL_PACKAGE_REPLACEMENTS[match.group(1)]
