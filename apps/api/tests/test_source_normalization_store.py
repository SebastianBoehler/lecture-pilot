import json
from pathlib import Path

import pytest

from lecturepilot.source_normalization_models import NormalizedDocument
from lecturepilot.source_normalization_store import (
    SourceNormalizationError,
    load_normalized_document,
)


SOURCE_SHA256 = "a" * 64


def test_normalized_document_retains_revision_bound_slide_locator(tmp_path: Path) -> None:
    _write_manifest(tmp_path, _manifest())

    document = load_normalized_document(tmp_path, SOURCE_SHA256)

    assert isinstance(document, NormalizedDocument)
    assert document.source_sha256 == SOURCE_SHA256
    assert document.blocks[0].locator.slide == 1
    assert document.blocks[0].locator.bbox == (10.0, 20.0, 300.0, 180.0)


def test_normalized_document_rejects_asset_outside_revision(tmp_path: Path) -> None:
    _write_manifest(tmp_path, _manifest(asset_path="../stolen.png"))

    with pytest.raises(SourceNormalizationError, match="inside the normalized revision"):
        load_normalized_document(tmp_path, SOURCE_SHA256)


def test_normalized_document_rejects_mismatched_source_revision(tmp_path: Path) -> None:
    _write_manifest(tmp_path, _manifest(source_sha256="b" * 64))

    with pytest.raises(SourceNormalizationError, match="does not match the requested revision"):
        load_normalized_document(tmp_path, SOURCE_SHA256)


def _write_manifest(root: Path, payload: dict) -> None:
    revision_root = root / SOURCE_SHA256
    revision_root.mkdir(parents=True)
    for block in payload["blocks"]:
        asset_path = block.get("asset_path")
        if asset_path and ".." not in Path(asset_path).parts:
            target = revision_root / asset_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"normalized asset")
    (revision_root / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")


def _manifest(
    *,
    source_sha256: str = SOURCE_SHA256,
    asset_path: str = "assets/slide-001.png",
) -> dict:
    return {
        "schema_version": 1,
        "source_path": "week-01/introduction.pptx",
        "source_sha256": source_sha256,
        "media_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "blocks": [
            {
                "kind": "image",
                "asset_path": asset_path,
                "locator": {"slide": 1, "bbox": [10, 20, 300, 180]},
                "extraction": "rendered",
            }
        ],
        "warnings": [],
    }
