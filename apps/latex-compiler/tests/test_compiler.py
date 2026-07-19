from __future__ import annotations

from pathlib import Path
import time
import zipfile

import pytest

from lecturepilot_latex_compiler.compiler import compile_archive
from lecturepilot_latex_compiler.errors import CompilerServiceError


def _archive(path: Path, *, main_path: str = "slides.tex") -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            main_path,
            "\\documentclass{beamer}\\begin{document}\\begin{frame}Hi\\end{frame}\\end{document}",
        )
    return path


def _fake_tectonic(path: Path, body: str) -> Path:
    path.write_text(
        f"""#!/bin/sh
set -eu
contains_line() {{
    needle=$1
    file=$2
    while IFS= read -r line; do
        test "$line" != "$needle" || return 0
    done < "$file"
    return 1
}}
{body}
""",
        encoding="utf-8",
    )
    path.chmod(0o700)
    return path


def test_forces_handout_and_uses_offline_cache(tmp_path: Path) -> None:
    fake = _fake_tectonic(
        tmp_path / "tectonic",
        """
case " $* " in *" --only-cached "*) ;; *) exit 7 ;; esac
test "$TECTONIC_CACHE_DIR" = /var/cache/tectonic
out=''
last=''
for arg in "$@"; do
    last=$arg
    case "$arg" in --outdir) next_is_out=1 ;; *)
        if test "${next_is_out:-0}" = 1; then out=$arg; next_is_out=0; fi ;;
    esac
done
contains_line '\\PassOptionsToClass{handout}{beamer}' "$last"
printf '%%PDF-1.7\nvalid' > "$out/${last%.tex}.pdf"
""",
    )

    result = compile_archive(
        _archive(tmp_path / "source.zip"),
        "slides.tex",
        tectonic_bin=str(fake),
    )

    assert result.startswith(b"%PDF-1.7")


def test_nested_main_can_read_support_files_from_its_directory_and_root(
    tmp_path: Path,
) -> None:
    fake = _fake_tectonic(
        tmp_path / "tectonic",
        r"""
test -f slides.tex
test -f shared.tex
out=''
last=''
for arg in "$@"; do
    last=$arg
    case "$arg" in --outdir) next_is_out=1 ;; *)
        if test "${next_is_out:-0}" = 1; then out=$arg; next_is_out=0; fi ;;
    esac
done
contains_line '\input{\detokenize{slides.tex}}' "$last"
printf '%%PDF-1.7\nvalid' > "$out/${last%.tex}.pdf"
""",
    )
    archive_path = _archive(
        tmp_path / "source.zip",
        main_path="schedule/slides.tex",
    )
    with zipfile.ZipFile(archive_path, "a", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("shared.tex", "root support file")

    result = compile_archive(
        archive_path,
        "schedule/slides.tex",
        tectonic_bin=str(fake),
    )

    assert result.startswith(b"%PDF-1.7")


def test_adds_case_correct_aliases_for_professor_asset_references(
    tmp_path: Path,
) -> None:
    fake = _fake_tectonic(
        tmp_path / "tectonic",
        r"""
test -f images/deepnets/initialization_xavier.png
out=''
last=''
for arg in "$@"; do
    last=$arg
    case "$arg" in --outdir) next_is_out=1 ;; *)
        if test "${next_is_out:-0}" = 1; then out=$arg; next_is_out=0; fi ;;
    esac
done
printf '%%PDF-1.7\nvalid' > "$out/${last%.tex}.pdf"
""",
    )
    archive_path = tmp_path / "source.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "slides.tex",
            "\\documentclass{beamer}\n"
            "\\graphicspath{{images/deepnets/}}\n"
            "\\begin{document}\\includegraphics{initialization_xavier}\\end{document}",
        )
        archive.writestr("images/deepnets/initialization_Xavier.png", b"image")

    result = compile_archive(
        archive_path,
        "slides.tex",
        tectonic_bin=str(fake),
    )

    assert result.startswith(b"%PDF-1.7")


def test_replaces_optional_visual_packages_with_standard_latex(tmp_path: Path) -> None:
    fake = _fake_tectonic(
        tmp_path / "tectonic",
        r"""
contains_line '\providecommand{\mathds}[1]{\mathbf{#1}}' slides.tex
contains_line '\providecommand{\epsdice}[1]{#1}' slides.tex
contains_line '\providecommand{\sout}[1]{#1}' slides.tex
if contains_line '\usepackage{dsfont}' slides.tex; then exit 9; fi
if contains_line '\usepackage{epsdice}' slides.tex; then exit 10; fi
if contains_line '\usepackage[normalem]{ulem}' slides.tex; then exit 11; fi
out=''
last=''
for arg in "$@"; do
    last=$arg
    case "$arg" in --outdir) next_is_out=1 ;; *)
        if test "${next_is_out:-0}" = 1; then out=$arg; next_is_out=0; fi ;;
    esac
done
printf '%%PDF-1.7\nvalid' > "$out/${last%.tex}.pdf"
""",
    )
    archive_path = _archive(tmp_path / "source.zip")
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "slides.tex",
            "\\documentclass{beamer}\n"
            "\\usepackage{dsfont}\n"
            "\\usepackage{epsdice}\n"
            "\\usepackage[normalem]{ulem}\n"
            "\\def\\indicator{\\mathds{1}}\n"
            "\\begin{document}\\begin{frame}Hi\\end{frame}\\end{document}",
        )

    result = compile_archive(
        archive_path,
        "slides.tex",
        tectonic_bin=str(fake),
    )

    assert result.startswith(b"%PDF-1.7")


def test_transcodes_explicit_latin1_sources_for_xetex(tmp_path: Path) -> None:
    fake = _fake_tectonic(
        tmp_path / "tectonic",
        r"""
contains_line '\usepackage[utf8]{inputenc}' legacy.tex
contains_line '\begin{document}Grüße\end{document}' legacy.tex
out=''
last=''
for arg in "$@"; do
    last=$arg
    case "$arg" in --outdir) next_is_out=1 ;; *)
        if test "${next_is_out:-0}" = 1; then out=$arg; next_is_out=0; fi ;;
    esac
done
printf '%%PDF-1.7\nvalid' > "$out/${last%.tex}.pdf"
""",
    )
    archive_path = tmp_path / "source.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "legacy.tex",
            b"\\documentclass{article}\n\\usepackage[latin1]{inputenc}\n"
            b"\\begin{document}Gr\xfc\xdfe\\end{document}\n",
        )

    result = compile_archive(
        archive_path,
        "legacy.tex",
        tectonic_bin=str(fake),
    )

    assert result.startswith(b"%PDF-1.7")


def test_timeout_kills_compile_promptly(tmp_path: Path) -> None:
    fake = _fake_tectonic(tmp_path / "tectonic", "while :; do :; done")
    started = time.monotonic()

    with pytest.raises(CompilerServiceError) as error:
        compile_archive(
            _archive(tmp_path / "source.zip"),
            "slides.tex",
            tectonic_bin=str(fake),
            timeout_seconds=0.2,
        )

    assert error.value.code == "compile_timeout"
    assert time.monotonic() - started < 3


def test_does_not_expose_compiler_output(tmp_path: Path) -> None:
    fake = _fake_tectonic(
        tmp_path / "tectonic", "echo 'private course text' >&2; exit 1"
    )

    with pytest.raises(CompilerServiceError) as error:
        compile_archive(
            _archive(tmp_path / "source.zip"),
            "slides.tex",
            tectonic_bin=str(fake),
        )

    assert error.value.code == "compile_failed"
    assert "private course text" not in error.value.message
