from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory


OFFICE_RENDER_TIMEOUT_SECONDS = 30


class OfficeRenderError(RuntimeError):
    pass


def render_office_pdf(source: Path, output: Path) -> None:
    executable = shutil.which("soffice")
    if executable is None:
        raise OfficeRenderError("LibreOffice is required to render this document.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="office-render-", dir=output.parent) as temporary:
        temporary_root = Path(temporary)
        profile = temporary_root / "profile"
        rendered = temporary_root / f"{source.stem}.pdf"
        command = [
            executable,
            "--headless",
            "--safe-mode",
            "--nologo",
            "--nodefault",
            "--nolockcheck",
            "--norestore",
            f"-env:UserInstallation={profile.resolve().as_uri()}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(temporary_root),
            str(source),
        ]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                timeout=OFFICE_RENDER_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise OfficeRenderError("Office document rendering timed out.") from exc
        if (
            completed.returncode
            or not rendered.is_file()
            or not rendered.read_bytes().startswith(b"%PDF-")
        ):
            raise OfficeRenderError("Office document rendering failed safely.")
        shutil.copyfile(rendered, output)
