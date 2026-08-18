from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from hashlib import sha256
import json
from pathlib import Path

from lecturepilot.canvas_models import CanvasSection
from lecturepilot.durable_files import atomic_write_json, exclusive_file_lock


SECTION_PLAN_VERSION = "3"
_active_store: ContextVar[SectionPlanCheckpointStore | None] = ContextVar(
    "lecturepilot_section_plan_checkpoint_store", default=None
)


class SectionPlanCheckpointStoreError(RuntimeError):
    pass


class SectionPlanCheckpointStore:
    """Durably cache completed evidence batches for safe generation resume."""

    def __init__(self, path: Path, *, source_revision: str) -> None:
        self.path = path
        self.source_revision = source_revision

    def read(
        self,
        source_section: CanvasSection,
        *,
        model: str,
        output_language: str,
    ) -> CanvasSection | None:
        key = _cache_key(source_section, model=model, output_language=output_language)
        with exclusive_file_lock(self.path):
            payload = self._read_payload()
            if payload.get("source_revision") != self.source_revision:
                return None
            raw = payload.get("sections", {}).get(key)
            if raw is None:
                return None
            try:
                return CanvasSection.model_validate(raw)
            except ValueError as exc:
                raise SectionPlanCheckpointStoreError(
                    "Stored canvas section checkpoint is invalid."
                ) from exc

    def write(
        self,
        source_section: CanvasSection,
        completed_section: CanvasSection,
        *,
        model: str,
        output_language: str,
    ) -> None:
        key = _cache_key(source_section, model=model, output_language=output_language)
        with exclusive_file_lock(self.path):
            payload = self._read_payload()
            if payload.get("source_revision") != self.source_revision:
                payload = {"source_revision": self.source_revision, "sections": {}}
            sections = payload.setdefault("sections", {})
            sections[key] = completed_section.model_dump(mode="json")
            atomic_write_json(self.path, payload)

    def _read_payload(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SectionPlanCheckpointStoreError(
                "Stored canvas section checkpoints could not be read."
            ) from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("sections", {}), dict):
            raise SectionPlanCheckpointStoreError("Stored canvas section checkpoints are invalid.")
        return payload


@contextmanager
def section_plan_checkpoint_scope(
    store: SectionPlanCheckpointStore,
) -> Iterator[None]:
    token = _active_store.set(store)
    try:
        yield
    finally:
        _active_store.reset(token)


def current_section_plan_checkpoint_store() -> SectionPlanCheckpointStore | None:
    return _active_store.get()


def _cache_key(section: CanvasSection, *, model: str, output_language: str) -> str:
    material = "\0".join((SECTION_PLAN_VERSION, model, output_language, section.model_dump_json()))
    return sha256(material.encode()).hexdigest()
