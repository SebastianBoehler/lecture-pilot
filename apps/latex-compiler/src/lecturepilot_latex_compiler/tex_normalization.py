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


def replace_optional_visual_dependencies(source_root: Path) -> None:
    for path in source_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _TEX_SOURCE_SUFFIXES:
            continue
        content = path.read_bytes()
        normalized = _OPTIONAL_PACKAGE.sub(_replace_optional_package, content)
        if normalized != content:
            path.write_bytes(normalized)


def _replace_optional_package(match: re.Match[bytes]) -> bytes:
    return _OPTIONAL_PACKAGE_REPLACEMENTS[match.group(1)]
