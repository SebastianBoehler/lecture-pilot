from datetime import UTC, datetime
from hashlib import sha256
import re

from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.durable_files import (
    atomic_write_json,
    ensure_durable_directory,
    exclusive_file_lock,
)
from lecturepilot.storage_layout import StorageLayout
from lecturepilot.workspace_capability import CapabilityRoot, WorkspaceCapability
from lecturepilot.workspace_fs import WorkspaceFS


class CanvasAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    section_id: str
    block_id: str
    block_digest: str
    publication_version: int
    quote: str = Field(max_length=500)
    comment: str = Field(min_length=1, max_length=2000)
    created_at: str


class AnnotationStore:
    """One private JSON file per comment, validated against its published passage."""

    def __init__(self, layout: StorageLayout, user_id: str, course_id: str, lecture_id: str):
        ensure_durable_directory(layout.root)
        self.fs = WorkspaceFS(
            WorkspaceCapability(roots=(CapabilityRoot("/annotations", layout.root, writable=True),))
        )
        relative = layout.user_lecture_root(user_id, course_id, lecture_id).relative_to(layout.root)
        self.logical_dir = f"/annotations/{relative.as_posix()}/annotations"
        self.directory = self.fs.resolve(self.logical_dir, for_write=True).path
        ensure_durable_directory(self.directory)

    def _path(self, annotation_id):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,119}", annotation_id):
            raise ValueError("Use a simple annotation filename ending in .json.")
        return self.fs.resolve(f"{self.logical_dir}/{annotation_id}.json", for_write=True).path

    def _read(self):
        notes = []
        for item in sorted(self.fs.files(self.logical_dir), key=lambda item: item.logical):
            if item.path.suffix != ".json" or item.path.parent != self.directory:
                raise ValueError("Annotations must be individual JSON files.")
            note = CanvasAnnotation.model_validate_json(self.fs.read_text(item.logical))
            if note.id != item.path.stem:
                raise ValueError("Annotation identity does not match its filename.")
            notes.append(note)
        return notes

    def list(self, document: CanvasDocument, version: int) -> list[CanvasAnnotation]:
        blocks = {
            block.id: (section.id, digest(block))
            for section in document.sections
            for block in section.blocks
        }
        return [
            note
            for note in self._read()
            if note.publication_version == version
            and blocks.get(note.block_id) == (note.section_id, note.block_digest)
        ]

    def save(self, document, version, annotation_id, values, *, expected_text=None):
        if not isinstance(values, dict):
            raise ValueError("An annotation file must contain one JSON object.")
        if values.keys() - CanvasAnnotation.model_fields.keys():
            raise ValueError(
                "Annotation files accept block_id, quote and comment; keep saved metadata unchanged."
            )
        path = self._path(annotation_id)
        with exclusive_file_lock(self.directory / "index"):
            current_text = (
                self.fs.read_text(f"{self.logical_dir}/{annotation_id}.json")
                if path.exists()
                else None
            )
            if expected_text is not None and current_text != expected_text:
                raise ValueError("Annotation changed. Read the file again before editing.")
            existing = CanvasAnnotation.model_validate_json(current_text) if current_text else None
            if existing and existing not in self.list(document, version):
                raise ValueError("The annotated passage has changed. Create a new annotation.")
            block_id = values.get("block_id")
            match = next(
                (
                    (section, block)
                    for section in document.sections
                    for block in section.blocks
                    if block.id == block_id
                ),
                None,
            )
            if match is None:
                raise ValueError("Annotation target must be an existing canvas block.")
            if existing and existing.block_id != block_id:
                raise ValueError("An annotation edit must keep its original passage.")
            section, block = match
            quote = values.get("quote", existing.quote if existing else "")
            comment = values.get("comment")
            if not isinstance(quote, str) or not isinstance(comment, str):
                raise ValueError("Annotation quote and comment must be text.")
            quote, comment = quote.strip(), comment.strip()
            if quote and quote not in " ".join([block.text or "", *block.items]):
                raise ValueError("Annotation quote must occur exactly in the target block.")
            note = CanvasAnnotation(
                id=annotation_id,
                section_id=section.id,
                block_id=block_id,
                block_digest=digest(block),
                publication_version=version,
                quote=quote,
                comment=comment,
                created_at=existing.created_at if existing else datetime.now(UTC).isoformat(),
            )
            for key in {"id", "section_id", "block_digest", "publication_version", "created_at"}:
                if key in values and values[key] != getattr(note, key):
                    raise ValueError(
                        f"Annotation metadata {key} is managed by the filesystem adapter."
                    )
            if not existing and len(self._read()) >= 100:
                raise ValueError(
                    "This lecture has 100 annotations. Delete a comment before adding another."
                )
            atomic_write_json(path, note.model_dump())
            return note

    def delete(self, annotation_id):
        path = self._path(annotation_id)
        with exclusive_file_lock(self.directory / "index"):
            if not path.exists():
                raise FileNotFoundError("Annotation not found.")
            path.unlink()


def digest(block) -> str:
    return sha256(block.model_dump_json().encode()).hexdigest()
