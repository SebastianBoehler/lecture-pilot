from __future__ import annotations

import os
from pathlib import Path

import pytest

from lecturepilot.source_bundle import scan_source_bundle
from lecturepilot.workspace_capability import CapabilityRoot, WorkspaceCapability
from lecturepilot.workspace_fs import WorkspaceFS, WorkspaceFSError


def test_workspace_fs_rejects_nested_file_and_directory_symlinks(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("outside secret", encoding="utf-8")
    (root / "file-link.txt").symlink_to(secret)
    (root / "directory-link").symlink_to(outside, target_is_directory=True)
    workspace = WorkspaceFS(WorkspaceCapability((CapabilityRoot("/root", root, writable=True),)))

    with pytest.raises(WorkspaceFSError, match="Symbolic links"):
        workspace.read_text("/root/file-link.txt")
    with pytest.raises(WorkspaceFSError, match="Symbolic links"):
        workspace.read_text("/root/directory-link/secret.txt")
    with pytest.raises(WorkspaceFSError, match="Symbolic links"):
        workspace.write_text("/root/directory-link/changed.txt", "changed")
    assert secret.read_text(encoding="utf-8") == "outside secret"


def test_workspace_fs_rejects_hardlinks_and_non_normalized_paths(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    source = root / "source.txt"
    source.write_text("protected", encoding="utf-8")
    os.link(source, root / "hard-link.txt")
    workspace = WorkspaceFS(WorkspaceCapability((CapabilityRoot("/root", root, writable=True),)))

    with pytest.raises(WorkspaceFSError, match="single-link"):
        workspace.read_text("/root/hard-link.txt")
    with pytest.raises(WorkspaceFSError, match="single-link"):
        workspace.files("/root")
    with pytest.raises(WorkspaceFSError, match="normalized Unicode"):
        workspace.resolve("/root/cafe\u0301.txt", for_write=True)


def test_source_bundle_rejects_symlinks_instead_of_following_them(tmp_path: Path) -> None:
    root = tmp_path / "source"
    outside = tmp_path / "outside.md"
    root.mkdir()
    outside.write_text("private", encoding="utf-8")
    (root / "escaped.md").symlink_to(outside)

    with pytest.raises(WorkspaceFSError, match="Symbolic links"):
        scan_source_bundle(root)
