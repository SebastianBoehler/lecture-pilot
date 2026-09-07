from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
from pathlib import Path
import re

from pydantic import ValidationError

from lecturepilot.canvas_markdown import section_to_markdown
from lecturepilot.canvas_markdown_blocks import read_blocks
from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.authoring_seed import seed_authoring_workspace
from lecturepilot.course_canvas_approved_checkpoints import assemble_approved_checkpoints
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_practice_contract import (
    practice_source_sections,
    section_target_assignments,
    validate_practice_candidate,
)
from lecturepilot.course_canvas_validation import validate_planned_document
from lecturepilot.course_practice_design_models import PracticeDesign
from lecturepilot.course_slide_interleaving import interleave_original_slides
from lecturepilot.durable_files import atomic_write_text
from lecturepilot.learning_map import validate_learning_contract_ids
from lecturepilot.quiz_identity import validate_unique_quiz_ids
from lecturepilot.storage_layout import safe_id
from lecturepilot.workspace_capability import CapabilityRoot, WorkspaceCapability
from lecturepilot.workspace_fs import WorkspaceFS, WorkspaceFSError


class AuthoringWorkspace:
    """Job-private Markdown drafts; identities and approved tasks stay server-owned."""

    def __init__(
        self,
        root: Path,
        source: CanvasDocument,
        design: PracticeDesign,
        authorize: Callable[[], None],
        candidate: CanvasDocument | None = None,
    ) -> None:
        self.source, self.design, self.authorize = source, design, authorize
        self.sections = practice_source_sections(source)
        self.targets = section_target_assignments(design, self.sections)
        self.paths = {f"/draft/{safe_id(s.id)}.md": s for s in self.sections}
        if len(self.paths) != len(self.sections) or not self.sections:
            raise ValueError("Authoring requires distinct source section paths.")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        for name in ("evidence", "draft"):
            (root / name).mkdir(exist_ok=True, mode=0o700)
        self.fs = WorkspaceFS(
            WorkspaceCapability(
                roots=(
                    CapabilityRoot("/evidence", root / "evidence"),
                    CapabilityRoot("/draft", root / "draft", writable=True),
                )
            )
        )
        for section in self.sections:
            atomic_write_text(
                root / "evidence" / f"{safe_id(section.id)}.md",
                section_to_markdown(section, inline_components=True),
            )
        self.originals = seed_authoring_workspace(self, root, candidate)

    def write(self, path: str, text: str) -> None:
        self.authorize()
        if path not in self.paths:
            raise WorkspaceFSError("Write only an assigned /draft/*.md path.")
        if len(text.encode()) > 200_000:
            raise WorkspaceFSError("A draft section cannot exceed 200 KB.")
        resolved = self.fs.resolve(path, for_write=True)
        atomic_write_text(resolved.path, text)

    def digest(self) -> str:
        contents = [
            (path, self.fs.read_text(path))
            for path in self.paths
            if self.fs.resolve(path, for_write=True).path.exists()
        ]
        return sha256(repr(contents).encode()).hexdigest()

    def document(self) -> CanvasDocument:
        self.authorize()
        sections: list[CanvasSection] = []
        defects: list[str] = []
        assets = {
            b.asset_path: b.asset_url
            for s in self.source.sections
            for b in s.blocks
            if b.type in {"asset", "video"} and b.asset_path
        }
        for path, source_section in self.paths.items():
            if not self.fs.resolve(path, for_write=True).path.exists():
                defects.append(f"Missing draft: {path}")
                continue
            body = self.fs.read_text(path)
            heading = re.match(r"^# ([^\n]{1,200})\n", body)
            blocks = read_blocks(
                body[heading.end() :] if heading else body,
                section_id=source_section.id,
                course_id=self.source.course_id,
                lecture_id=self.source.lecture_id,
            )
            if not blocks or not any(b.text or b.items or b.component_data for b in blocks):
                raise CanvasGenerationRepairableError(f"Draft has no teaching content: {path}")
            for block in blocks:
                if block.type in {"asset", "video"}:
                    if block.asset_path not in assets:
                        raise CanvasGenerationRepairableError(f"Unknown course asset in {path}.")
                    block.asset_url = assets[block.asset_path]
            original = self.originals.get(source_section.id)
            section = CanvasSection(
                id=original.id if original else f"learning-{source_section.id}"[:120],
                title=heading.group(1) if heading else source_section.title,
                source_ref=source_section.source_ref,
                source_section_id=source_section.id,
                blocks=blocks,
            )
            section = assemble_approved_checkpoints(section, self.targets[source_section.id])
            try:
                validate_planned_document(
                    self.source.model_copy(update={"sections": [section]}), self.source
                )
            except CanvasGenerationRepairableError as exc:
                defects.append(f"{path}: {exc}")
            sections.append(section)
        if defects:
            raise CanvasGenerationRepairableError(
                "Repair all reported sections:\n" + "\n".join(defects)
            )
        document = self.source.model_copy(update={"source_kind": "generated", "sections": sections})
        document = interleave_original_slides(document, self.source)
        validate_planned_document(document, self.source)
        validate_practice_candidate(document, self.design, source_document=self.source)
        validate_unique_quiz_ids(document)
        validate_learning_contract_ids(document)
        return document


AUTHORING_INPUT_ERRORS = (
    CanvasGenerationRepairableError,
    WorkspaceFSError,
    ValidationError,
    ValueError,
)
