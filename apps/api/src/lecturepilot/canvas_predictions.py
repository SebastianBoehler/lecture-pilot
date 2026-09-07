"""Private, publication-bound first guesses; deliberately separate from gate evidence."""

from datetime import UTC, datetime
from hashlib import sha256

from lecturepilot.canvas_prediction_models import CanvasPrediction

from lecturepilot.canvas_annotations import digest
from lecturepilot.durable_files import (
    atomic_write_json,
    ensure_durable_directory,
    exclusive_file_lock,
)
from lecturepilot.workspace_capability import CapabilityRoot, WorkspaceCapability
from lecturepilot.workspace_fs import WorkspaceFS


class PredictionStore:
    def __init__(self, layout, user_id, course_id, lecture_id):
        ensure_durable_directory(layout.root)
        self.fs = WorkspaceFS(
            WorkspaceCapability(roots=(CapabilityRoot("/predictions", layout.root, writable=True),))
        )
        relative = layout.user_lecture_root(user_id, course_id, lecture_id).relative_to(layout.root)
        self.logical = f"/predictions/{relative.as_posix()}/predictions"
        self.directory = self.fs.resolve(self.logical, for_write=True).path
        ensure_durable_directory(self.directory)

    def list(self, document, version):
        result = []
        for section in document.sections:
            for block in section.blocks:
                if block.type != "prediction":
                    continue
                logical = self._logical(block.id)
                if not self.fs.resolve(logical, for_write=True).path.exists():
                    continue
                saved = CanvasPrediction.model_validate_json(self.fs.read_text(logical))
                if (
                    saved.block_id == block.id
                    and saved.section_id == section.id
                    and saved.publication_version == version
                    and saved.block_digest == digest(block)
                ):
                    result.append(saved)
        return result

    def _logical(self, block_id):
        return f"{self.logical}/{sha256(block_id.encode()).hexdigest()}.json"

    def save(self, document, version, block_id, answer):
        match = next(
            (
                (section, block)
                for section in document.sections
                for block in section.blocks
                if block.id == block_id and block.type == "prediction"
            ),
            None,
        )
        if match is None:
            raise ValueError("Prediction must target a published prediction card.")
        if answer is not None:
            answer = answer.strip()
            if not answer or len(answer) > 2000:
                raise ValueError("Enter a prediction of 1–2000 characters, or skip.")
        section, block = match
        with exclusive_file_lock(self.directory / "index"):
            existing = next(
                (item for item in self.list(document, version) if item.block_id == block_id), None
            )
            if existing:
                if existing.answer != answer:
                    raise ValueError("Your first prediction is already saved for this question.")
                return existing
            saved = CanvasPrediction(
                block_id=block_id,
                section_id=section.id,
                block_digest=digest(block),
                publication_version=version,
                question=block.text or "",
                answer=answer,
                created_at=datetime.now(UTC).isoformat(),
            )
            atomic_write_json(
                self.fs.resolve(self._logical(block_id), for_write=True).path, saved.model_dump()
            )
            return saved


def prediction_context(workspace, turn):
    """Only current predictions reach the tutor, never an independent assessment."""
    from lecturepilot.agent_annotation import require_annotation_access

    try:
        require_annotation_access(workspace.layout, turn.user_id, turn.course_id, turn.lecture_id)
    except ValueError:
        return []
    snapshot = workspace.read_published_canvas_view(
        user_id=turn.user_id,
        course_id=turn.course_id,
        lecture_id=turn.lecture_id,
    )
    if snapshot is None:
        return []
    return PredictionStore(workspace.layout, turn.user_id, turn.course_id, turn.lecture_id).list(
        snapshot.document,
        snapshot.version,
    )[:1]
