"""Application boundary for the framework-owned authoring loop."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

from lecturepilot.authoring_job import AuthoringJob, run_authoring_job
from lecturepilot.authoring_models import AuthoringMetrics
from lecturepilot.authoring_provider import authoring_model
from lecturepilot.authoring_checkpoint_review import CheckpointReviewer
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_quality import CanvasQualityReviewer, LiteLLMCanvasQualityClient
from lecturepilot.course_content_filter import filter_source_document_for_planning
from lecturepilot.course_practice_design_models import PracticeDesign
from lecturepilot.model_usage import ModelUsageRecorder
from lecturepilot.models import ProviderCapability
from lecturepilot.providers import ProviderRegistry


@dataclass(frozen=True)
class AuthoringScope:
    root: Path
    source_revision: str
    authorize: Callable[[], None]
    candidate: CanvasDocument | None = None
    report: Callable[[AuthoringMetrics], None] = lambda metrics: None


_scope: ContextVar[AuthoringScope | None] = ContextVar("canvas_authoring_scope", default=None)


@contextmanager
def authoring_scope(scope: AuthoringScope) -> Iterator[None]:
    token = _scope.set(scope)
    try:
        yield
    finally:
        _scope.reset(token)


class CourseCanvasAuthor:
    def __init__(self, usage_recorder: ModelUsageRecorder | None = None):
        self.provider_registry = ProviderRegistry.from_env()
        self.usage_recorder = usage_recorder
        self.reviewer = CanvasQualityReviewer(LiteLLMCanvasQualityClient(usage_recorder))

    async def plan_canvas(
        self,
        source_document: CanvasDocument,
        *,
        practice_design: PracticeDesign,
        output_language: str = "en",
        repair_context: str | None = None,
    ) -> CanvasDocument:
        scope = _scope.get()
        if scope is None:
            raise RuntimeError("Canvas authoring requires an authorized durable job scope.")
        scope.authorize()
        settings = self.provider_registry.require_ready(
            [ProviderCapability.CHAT, ProviderCapability.TOOL_CALLS]
        )
        job = AuthoringJob(
            root=scope.root,
            source=filter_source_document_for_planning(source_document),
            design=practice_design,
            source_revision=scope.source_revision,
            settings=settings,
            reviewer=self.reviewer,
            checkpoint_reviewer=CheckpointReviewer(self.usage_recorder),
            output_language=output_language,
            authorize=scope.authorize,
            repair_context=repair_context,
            candidate=scope.candidate,
            report=scope.report,
        )
        async with authoring_model(settings, self.usage_recorder, scope.authorize) as model:
            result = await run_authoring_job(job, model=model)
        return result.document
