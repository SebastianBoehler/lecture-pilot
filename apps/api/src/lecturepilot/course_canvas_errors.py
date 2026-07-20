from __future__ import annotations

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.providers import ProviderConfigurationError


class CanvasGenerationRepairableError(ProviderConfigurationError):
    """A deterministic generated-draft failure that can be repaired from source evidence."""

    def __init__(
        self,
        message: str,
        *,
        candidate: CanvasDocument | None = None,
        section_id: str | None = None,
        block_id: str | None = None,
        source_revision: str | None = None,
    ) -> None:
        super().__init__(message)
        self.candidate = candidate
        self.section_id = section_id
        self.block_id = block_id
        self.source_revision = source_revision

    def with_candidate(self, candidate: CanvasDocument) -> CanvasGenerationRepairableError:
        self.candidate = candidate
        return self

    def with_source_revision(self, source_revision: str | None) -> CanvasGenerationRepairableError:
        self.source_revision = source_revision
        return self
