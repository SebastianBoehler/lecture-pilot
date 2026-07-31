from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import os
from pathlib import Path
import re
import shutil
import tempfile

from lecturepilot.durable_files import atomic_write_json, ensure_durable_directory, fsync_directory
from lecturepilot.ppi_exam_source_archive import normalize_ppi_archive
from lecturepilot.ppi_exam_source_models import PpiExamSourceManifest
from lecturepilot.storage_layout import StorageLayout


_SOURCE_ID = re.compile(r"^ppi-[1-9][0-9]*$")


class PpiExamSourceStore:
    def __init__(self, layout: StorageLayout) -> None:
        self.layout = layout

    def import_archive(
        self,
        *,
        user_id: str,
        course_id: str,
        lecture_id: int,
        title: str,
        protocol_count: int,
        filename: str,
        archive: bytes,
        borrowed_until: str | None = None,
    ) -> PpiExamSourceManifest:
        source_id = f"ppi-{lecture_id}"
        target = self.layout.ppi_exam_source_dir(user_id, course_id, source_id)
        if target.exists():
            return self.read(user_id=user_id, course_id=course_id, source_id=source_id)
        parent = self.layout.ppi_exam_sources_dir(user_id, course_id)
        ensure_durable_directory(parent)
        stage = Path(tempfile.mkdtemp(prefix=".ppi-import-", dir=parent))
        try:
            archive_path = stage / "source.zip"
            _write_private_bytes(archive_path, archive)
            files = normalize_ppi_archive(archive, output_root=stage)
            manifest = PpiExamSourceManifest(
                id=source_id,
                ppi_lecture_id=lecture_id,
                title=title,
                protocol_count=protocol_count,
                imported_at=datetime.now(UTC),
                borrowed_until=borrowed_until,
                source_filename=_safe_filename(filename),
                archive_sha256=sha256(archive).hexdigest(),
                files=files,
            )
            atomic_write_json(stage / "manifest.json", manifest.model_dump(mode="json"))
            stage.replace(target)
            fsync_directory(parent)
            return manifest
        except BaseException:
            shutil.rmtree(stage, ignore_errors=True)
            if target.exists():
                return self.read(user_id=user_id, course_id=course_id, source_id=source_id)
            raise

    def read(self, *, user_id: str, course_id: str, source_id: str) -> PpiExamSourceManifest:
        path = self._source_dir(user_id, course_id, source_id) / "manifest.json"
        if not path.is_file():
            raise FileNotFoundError(source_id)
        return PpiExamSourceManifest.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self, *, user_id: str, course_id: str) -> list[PpiExamSourceManifest]:
        root = self.layout.ppi_exam_sources_dir(user_id, course_id)
        if not root.is_dir():
            return []
        sources = [
            PpiExamSourceManifest.model_validate_json(path.read_text(encoding="utf-8"))
            for path in root.glob("ppi-*/manifest.json")
        ]
        return sorted(sources, key=lambda item: (item.imported_at, item.id), reverse=True)

    def delete(self, *, user_id: str, course_id: str, source_id: str) -> bool:
        target = self._source_dir(user_id, course_id, source_id)
        if not target.exists():
            return False
        shutil.rmtree(target)
        fsync_directory(target.parent)
        return True

    def normalized_text(
        self, *, user_id: str, course_id: str, source_id: str
    ) -> list[tuple[str, str]]:
        manifest = self.read(user_id=user_id, course_id=course_id, source_id=source_id)
        root = self._source_dir(user_id, course_id, source_id)
        return [
            (item.path, (root / item.text_path).read_text(encoding="utf-8"))
            for item in manifest.files
        ]

    def _source_dir(self, user_id: str, course_id: str, source_id: str) -> Path:
        if not _SOURCE_ID.fullmatch(source_id):
            raise FileNotFoundError(source_id)
        return self.layout.ppi_exam_source_dir(user_id, course_id, source_id)


def _write_private_bytes(path: Path, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _safe_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    if not name or name.startswith(".") or len(name) > 240:
        raise ValueError("PPI download filename is invalid.")
    return name
