from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lecturepilot import learning_map as learning_maps
from lecturepilot.canvas_learning_support import normalize_learning_support
from lecturepilot.canvas_markdown import read_document_source
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.canvas_snapshot import locked_canvas_paths
from lecturepilot.course_canvas_publication import read_publication


@dataclass(frozen=True)
class PublishedCanvasSnapshot:
    document: CanvasDocument
    publication: dict
    version: int
    learning_map_revision: str


@dataclass(frozen=True)
class AnalyticsPublicationContext:
    learning_map: learning_maps.LearningMap
    publication_version: int
    learning_map_revision: str


class InvalidPublishedCanvasContextError(RuntimeError):
    pass


class StalePublishedCanvasVersionError(RuntimeError):
    pass


def read_published_snapshot(
    published_dir: Path, *, expected_version: int
) -> PublishedCanvasSnapshot | None:
    with locked_canvas_paths(published_dir):
        if not (published_dir / "index.md").exists():
            return None
        publication = read_publication(published_dir)
        if publication is None:
            raise InvalidPublishedCanvasContextError(
                "Published canvas is missing publication metadata. Publish it again."
            )
        version = _required_publication_version(publication)
        if version != expected_version:
            raise StalePublishedCanvasVersionError
        learning_map = _required_learning_map(published_dir, publication)
        document = normalize_learning_support(read_document_source(published_dir)).model_copy(
            update={"workspace_path": str(published_dir / "index.md")}
        )
        return PublishedCanvasSnapshot(
            document=document,
            publication=publication,
            version=version,
            learning_map_revision=learning_map.revision,
        )


def read_analytics_context(published_dir: Path) -> AnalyticsPublicationContext:
    with locked_canvas_paths(published_dir):
        publication = read_publication(published_dir)
        if publication is None:
            raise InvalidPublishedCanvasContextError(
                "Published canvas is missing publication metadata. Publish it again."
            )
        version = _required_publication_version(publication)
        learning_map = _required_learning_map(published_dir, publication)
        return AnalyticsPublicationContext(
            learning_map=learning_map,
            publication_version=version,
            learning_map_revision=learning_map.revision,
        )


def _required_learning_map(published_dir: Path, publication: dict) -> learning_maps.LearningMap:
    learning_map = learning_maps.read_learning_map(published_dir)
    if learning_map is None:
        raise InvalidPublishedCanvasContextError(
            "Published canvas is missing its learning map. Publish the canvas again."
        )
    if publication.get("learning_map_revision") != learning_map.revision:
        raise InvalidPublishedCanvasContextError(
            "Published canvas metadata does not match its learning map. Publish it again."
        )
    if any(not gate.revision for gate in learning_map.gates):
        raise InvalidPublishedCanvasContextError(
            "Published canvas contains an unversioned gate. Publish it again."
        )
    return learning_map


def _required_publication_version(publication: dict) -> int:
    version = publication.get("version")
    if not isinstance(version, int) or version < 1:
        raise InvalidPublishedCanvasContextError(
            "Published canvas is missing valid publication metadata. Publish it again."
        )
    return version
