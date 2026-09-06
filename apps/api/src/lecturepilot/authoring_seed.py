"""Import a revision-checked failed draft without exposing mutable identity files."""

from pathlib import Path

from lecturepilot.canvas_internal_serialization import canvas_document_internal_payload
from lecturepilot.canvas_markdown_blocks import block_to_markdown
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.durable_files import atomic_write_json


def seed_authoring_workspace(workspace, root: Path, candidate: CanvasDocument | None):
    path = root / "initial-draft.json"
    if path.exists():
        candidate = CanvasDocument.model_validate_json(path.read_text())
    if candidate is not None:
        if (candidate.course_id, candidate.lecture_id) != (
            workspace.source.course_id,
            workspace.source.lecture_id,
        ):
            raise ValueError("Repair candidate belongs to another lecture.")
        source_ids = {s.id for s in workspace.sections}
        identities = [s.source_section_id for s in candidate.sections]
        if any(s not in source_ids for s in identities) or len(set(identities)) != len(identities):
            raise ValueError("Repair candidate has incompatible source-section identities.")
        if not path.exists():
            atomic_write_json(path, canvas_document_internal_payload(candidate))
    if candidate is None:
        return {}
    originals = {s.source_section_id: s for s in candidate.sections}
    for draft_path, source_section in workspace.paths.items():
        original = originals.get(source_section.id)
        if (
            original is not None
            and not workspace.fs.resolve(draft_path, for_write=True).path.exists()
        ):
            text = f"# {original.title}\n\n" + "\n\n".join(
                block_to_markdown(block, inline_components=True)
                for block in original.blocks
                if not block.id.startswith("practice-")
            )
            workspace.write(draft_path, text)
    return originals
