from __future__ import annotations

from pathlib import Path, PurePosixPath

from pydantic import ValidationError

from lecturepilot.source_normalization_models import NormalizedDocument
from lecturepilot.workspace_capability import CapabilityRoot, WorkspaceCapability
from lecturepilot.workspace_fs import WorkspaceFS, WorkspaceFSError


class SourceNormalizationError(RuntimeError):
    pass


def load_normalized_document(root: Path, sha256: str) -> NormalizedDocument:
    revision_root = root / sha256
    workspace = WorkspaceFS(
        WorkspaceCapability((CapabilityRoot("/revision", revision_root, writable=False),))
    )
    try:
        document = NormalizedDocument.model_validate_json(
            workspace.read_text("/revision/manifest.json")
        )
    except (ValidationError, WorkspaceFSError) as exc:
        raise SourceNormalizationError(
            "Normalized source manifest is invalid or unavailable."
        ) from exc
    if document.source_sha256 != sha256:
        raise SourceNormalizationError("Normalized source does not match the requested revision.")
    for block in document.blocks:
        if block.asset_path:
            _validate_asset(workspace, block.asset_path)
    return document


def _validate_asset(workspace: WorkspaceFS, asset_path: str) -> None:
    relative = PurePosixPath(asset_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise SourceNormalizationError(
            "Normalized assets must stay inside the normalized revision."
        )
    try:
        workspace.resolve(f"/revision/{relative.as_posix()}")
    except WorkspaceFSError as exc:
        raise SourceNormalizationError(
            "Normalized assets must stay inside the normalized revision."
        ) from exc
