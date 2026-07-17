from __future__ import annotations

from collections.abc import Callable

import os
from pathlib import Path
import resource
import secrets
import signal
import subprocess
import sys
import tempfile
import time

from lecturepilot_latex_compiler.archive import (
    extract_source_archive,
    safe_relative_path,
)
from lecturepilot_latex_compiler.errors import (
    COMPILE_FAILED,
    COMPILE_TIMEOUT,
    INVALID_OUTPUT,
    MAIN_UNAVAILABLE,
    CompilerServiceError,
)
from lecturepilot_latex_compiler.limits import (
    COMPILE_CPU_SECONDS,
    COMPILE_MEMORY_BYTES,
    COMPILE_OPEN_FILES,
    COMPILE_PROCESSES,
    COMPILE_WALL_SECONDS,
    MAX_OUTPUT_BYTES,
)
from lecturepilot_latex_compiler.tex_normalization import (
    replace_optional_visual_dependencies,
)


def compile_archive(
    archive_path: Path,
    main_path: str,
    *,
    pdflatex_bin: str = "/usr/bin/pdflatex",
    timeout_seconds: float = COMPILE_WALL_SECONDS,
) -> bytes:
    with tempfile.TemporaryDirectory(prefix="lecturepilot-latex-") as temporary:
        job_root = Path(temporary)
        source_root = job_root / "source"
        output_root = job_root / "output"
        extract_source_archive(archive_path, source_root)
        replace_optional_visual_dependencies(source_root)
        main = _resolve_main(source_root, main_path)
        output_root.mkdir(mode=0o700)
        wrapper = _write_handout_wrapper(main)
        pdf_path = _run_pdflatex(
            wrapper=wrapper,
            source_root=source_root,
            output_root=output_root,
            pdflatex_bin=pdflatex_bin,
            timeout_seconds=timeout_seconds,
        )
        return _read_pdf(pdf_path)


def _resolve_main(source_root: Path, value: str) -> Path:
    try:
        relative = safe_relative_path(value)
    except CompilerServiceError as exc:
        raise CompilerServiceError(
            "main_unavailable", MAIN_UNAVAILABLE, status=400
        ) from exc
    if relative.suffix.lower() != ".tex" or any(
        character in relative.as_posix() for character in "{}%#\\"
    ):
        raise CompilerServiceError("main_unavailable", MAIN_UNAVAILABLE, status=400)
    main = source_root.joinpath(*relative.parts)
    if not main.is_file() or main.is_symlink():
        raise CompilerServiceError("main_unavailable", MAIN_UNAVAILABLE, status=404)
    return main


def _write_handout_wrapper(main: Path) -> Path:
    wrapper = main.parent / f"lecturepilot-{secrets.token_hex(12)}.tex"
    wrapper.write_text(
        "\\PassOptionsToClass{handout}{beamer}\n"
        f"\\input{{\\detokenize{{{main.name}}}}}\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o600)
    return wrapper


def _run_pdflatex(
    *,
    wrapper: Path,
    source_root: Path,
    output_root: Path,
    pdflatex_bin: str,
    timeout_seconds: float,
) -> Path:
    command = [
        pdflatex_bin,
        "-no-shell-escape",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        "-recorder",
        "-jobname=lecturepilot-slides",
        f"-output-directory={output_root}",
        wrapper.name,
    ]
    process_command, process_limits = _process_command(command)
    deadline = time.monotonic() + max(0.1, timeout_seconds)
    transcript_path = output_root / "compiler-output.txt"
    try:
        with transcript_path.open("wb") as transcript:
            for _ in range(2):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise CompilerServiceError(
                        "compile_timeout", COMPILE_TIMEOUT, status=504
                    )
                process = subprocess.Popen(
                    process_command,
                    cwd=wrapper.parent,
                    env=_compiler_environment(source_root, output_root),
                    stdin=subprocess.DEVNULL,
                    stdout=transcript,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    preexec_fn=process_limits,
                )
                try:
                    return_code = process.wait(timeout=remaining)
                except subprocess.TimeoutExpired as exc:
                    _kill_process_group(process)
                    raise CompilerServiceError(
                        "compile_timeout", COMPILE_TIMEOUT, status=504
                    ) from exc
                if return_code != 0:
                    raise CompilerServiceError("compile_failed", COMPILE_FAILED)
    except FileNotFoundError as exc:
        raise CompilerServiceError(
            "compiler_unavailable", COMPILE_FAILED, status=503
        ) from exc
    except (OSError, subprocess.SubprocessError) as exc:
        raise CompilerServiceError("compile_failed", COMPILE_FAILED) from exc
    return output_root / "lecturepilot-slides.pdf"


def _compiler_environment(source_root: Path, output_root: Path) -> dict[str, str]:
    return {
        "HOME": str(output_root),
        "LANG": "C.UTF-8",
        "PATH": "/usr/bin:/bin",
        "SHELL": "/bin/false",
        "TEXINPUTS": f".:{source_root}//:",
        "TEXMFOUTPUT": str(output_root),
        "openin_any": "p",
        "openout_any": "p",
        "shell_escape": "0",
    }


def _process_command(
    command: list[str],
) -> tuple[list[str], Callable[[], None] | None]:
    if sys.platform.startswith("linux"):
        return (
            [
                "/usr/bin/prlimit",
                f"--cpu={COMPILE_CPU_SECONDS}",
                f"--as={COMPILE_MEMORY_BYTES}",
                f"--fsize={MAX_OUTPUT_BYTES}",
                f"--nofile={COMPILE_OPEN_FILES}",
                f"--nproc={COMPILE_PROCESSES}",
                "--core=0",
                "--",
                *command,
            ],
            None,
        )
    return command, _apply_process_limits if os.name == "posix" else None


def _apply_process_limits() -> None:
    _set_limit(resource.RLIMIT_CPU, COMPILE_CPU_SECONDS)
    _set_limit(resource.RLIMIT_FSIZE, MAX_OUTPUT_BYTES)
    _set_limit(resource.RLIMIT_NOFILE, COMPILE_OPEN_FILES)
    _set_limit(resource.RLIMIT_CORE, 0)


def _set_limit(kind: int, requested: int) -> None:
    _, hard = resource.getrlimit(kind)
    soft = requested if hard == resource.RLIM_INFINITY else min(requested, hard)
    resource.setrlimit(kind, (soft, hard))


def _kill_process_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def _read_pdf(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise CompilerServiceError("invalid_output", INVALID_OUTPUT)
    size = path.stat().st_size
    if size < 8 or size > MAX_OUTPUT_BYTES:
        raise CompilerServiceError("invalid_output", INVALID_OUTPUT)
    content = path.read_bytes()
    if not content.startswith(b"%PDF-"):
        raise CompilerServiceError("invalid_output", INVALID_OUTPUT)
    return content
