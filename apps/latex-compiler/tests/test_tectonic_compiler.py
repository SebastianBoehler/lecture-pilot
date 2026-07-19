from __future__ import annotations

from pathlib import Path
import zipfile

from lecturepilot_latex_compiler.compiler import compile_archive


def _archive(path: Path) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "slides.tex",
            "\\documentclass{beamer}"
            "\\begin{document}\\begin{frame}Hi\\end{frame}\\end{document}",
        )
    return path


def _fake_tectonic(path: Path) -> Path:
    path.write_text(
        r"""#!/bin/sh
set -eu
contains_line() {
    needle=$1
    file=$2
    while IFS= read -r line; do
        test "$line" != "$needle" || return 0
    done < "$file"
    return 1
}
case " $* " in *" --only-cached "*) ;; *) exit 7 ;; esac
case " $* " in *" --untrusted "*) ;; *) exit 8 ;; esac
case " $* " in *" --bundle https://data1.fullyjustified.net/tlextras-2022.0r0.tar "*) ;; *) exit 9 ;; esac
test "$TECTONIC_CACHE_DIR" = /var/cache/tectonic
out=''
last=''
previous=''
for arg in "$@"; do
    if test "$previous" = --outdir; then out=$arg; fi
    previous=$arg
    last=$arg
done
contains_line '\PassOptionsToClass{handout}{beamer}' "$last"
contains_line '\AtBeginDocument{\ifcsname movie\endcsname\renewcommand{\movie}[3][]{#2}\fi}' "$last"
printf '%%PDF-1.7\nvalid' > "$out/${last%.tex}.pdf"
""",
        encoding="utf-8",
    )
    path.chmod(0o700)
    return path


def test_uses_offline_untrusted_tectonic_with_lecturepilot_adapter(
    tmp_path: Path,
) -> None:
    result = compile_archive(
        _archive(tmp_path / "source.zip"),
        "slides.tex",
        tectonic_bin=str(_fake_tectonic(tmp_path / "tectonic")),
    )

    assert result.startswith(b"%PDF-1.7")
