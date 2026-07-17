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


def _fake_pdflatex(path: Path, body: str) -> Path:
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


def test_forces_handout_and_disables_shell_escape(tmp_path: Path) -> None:
    fake = _fake_pdflatex(
        tmp_path / "pdflatex",
        """
case " $* " in *" -no-shell-escape "*) ;; *) exit 7 ;; esac
test "$openin_any" = p
test "$openout_any" = p
test "$shell_escape" = 0
out=''
last=''
for arg in "$@"; do
    last=$arg
    case "$arg" in -output-directory=*) out=${arg#*=} ;; esac
done
contains_line '\\PassOptionsToClass{handout}{beamer}' "$last"
printf '%%PDF-1.7\nvalid' > "$out/lecturepilot-slides.pdf"
""",
    )

    result = compile_archive(
        _archive(tmp_path / "source.zip"),
        "slides.tex",
        pdflatex_bin=str(fake),
    )

    assert result.startswith(b"%PDF-1.7")


def test_nested_main_uses_its_directory_and_root_texinputs(tmp_path: Path) -> None:
    fake = _fake_pdflatex(
        tmp_path / "pdflatex",
        r"""
test -f slides.tex
test -f ../shared.tex
case "$TEXINPUTS" in */source//:) ;; *) exit 8 ;; esac
out=''
last=''
for arg in "$@"; do
    last=$arg
    case "$arg" in -output-directory=*) out=${arg#*=} ;; esac
done
contains_line '\input{\detokenize{slides.tex}}' "$last"
printf '%%PDF-1.7\nvalid' > "$out/lecturepilot-slides.pdf"
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
        pdflatex_bin=str(fake),
    )

    assert result.startswith(b"%PDF-1.7")


def test_replaces_optional_visual_packages_with_standard_latex(tmp_path: Path) -> None:
    fake = _fake_pdflatex(
        tmp_path / "pdflatex",
        r"""
contains_line '\providecommand{\mathds}[1]{\mathbf{#1}}' slides.tex
contains_line '\providecommand{\epsdice}[1]{#1}' slides.tex
contains_line '\providecommand{\sout}[1]{#1}' slides.tex
if contains_line '\usepackage{dsfont}' slides.tex; then exit 9; fi
if contains_line '\usepackage{epsdice}' slides.tex; then exit 10; fi
if contains_line '\usepackage[normalem]{ulem}' slides.tex; then exit 11; fi
out=''
for arg in "$@"; do
    case "$arg" in -output-directory=*) out=${arg#*=} ;; esac
done
printf '%%PDF-1.7\nvalid' > "$out/lecturepilot-slides.pdf"
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
        pdflatex_bin=str(fake),
    )

    assert result.startswith(b"%PDF-1.7")


def test_timeout_kills_compile_promptly(tmp_path: Path) -> None:
    fake = _fake_pdflatex(tmp_path / "pdflatex", "while :; do :; done")
    started = time.monotonic()

    with pytest.raises(CompilerServiceError) as error:
        compile_archive(
            _archive(tmp_path / "source.zip"),
            "slides.tex",
            pdflatex_bin=str(fake),
            timeout_seconds=0.2,
        )

    assert error.value.code == "compile_timeout"
    assert time.monotonic() - started < 3


def test_does_not_expose_compiler_output(tmp_path: Path) -> None:
    fake = _fake_pdflatex(
        tmp_path / "pdflatex", "echo 'private course text' >&2; exit 1"
    )

    with pytest.raises(CompilerServiceError) as error:
        compile_archive(
            _archive(tmp_path / "source.zip"),
            "slides.tex",
            pdflatex_bin=str(fake),
        )

    assert error.value.code == "compile_failed"
    assert "private course text" not in error.value.message
