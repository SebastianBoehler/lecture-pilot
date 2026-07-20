from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.lecture_access_models import (
    CourseAccessPolicy,
    LectureAccessRule,
    LectureReleaseStatus,
    PublicationMode,
)
from lecturepilot.quality_gate_models import (
    QualityGateDecision,
    QualityGateStatus as QualityGateStatus,
)
from lecturepilot.scaffold_policy import AssistanceLevel, TutorScaffoldPolicy


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"


class ProviderCapability(StrEnum):
    CHAT = "chat"
    TOOL_CALLS = "tool_calls"
    STRUCTURED_JSON = "structured_json"
    LONG_CONTEXT = "long_context"


class TenantRole(StrEnum):
    TENANT_ADMIN = "tenant_admin"
    PROFESSOR = "professor"
    TUTOR = "tutor"
    STUDENT = "student"


class Tenant(BaseModel):
    id: str = Field(min_length=8, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    domain: str | None = Field(default=None, max_length=200)


class TenantMembership(BaseModel):
    tenant_id: str = Field(min_length=8, max_length=120)
    role: TenantRole


class UserProfile(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    username: str = Field(min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=320)
    display_name: str | None = Field(default=None, max_length=200)
    memberships: list[TenantMembership] = Field(default_factory=list)


class Course(BaseModel):
    id: str
    title: str
    professor: str
    term: str
    canvas_language: Literal["de", "en"] = "en"
    access_policy: CourseAccessPolicy = CourseAccessPolicy.TUEBINGEN_ENROLLED
    default_publication_mode: PublicationMode = PublicationMode.ON_LECTURE_DATE


class Lecture(BaseModel):
    id: str
    course_id: str
    title: str
    date: date
    material_path: str | None = None
    access_override: LectureAccessRule | None = None


class LectureView(BaseModel):
    lecture: Lecture
    unlocked: bool
    attendance: AttendanceStatus = AttendanceStatus.UNKNOWN
    release_status: LectureReleaseStatus = LectureReleaseStatus.RELEASED
    effective_publication_at: datetime | None = None
    content_ready: bool = False


class SourceBundleEntry(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    kind: str = Field(min_length=1, max_length=80)
    size_bytes: int = Field(ge=0)


class CourseMaterialUploadType(BaseModel):
    suffix: str = Field(min_length=2, max_length=20)
    kind: str = Field(min_length=1, max_length=80)
    max_bytes: int = Field(gt=0)


class SourceBundleManifest(BaseModel):
    course_id: str = Field(min_length=1)
    files: list[SourceBundleEntry]
    counts_by_kind: dict[str, int]
    supported_uploads: list[CourseMaterialUploadType]


class CourseMaterialUploadResult(BaseModel):
    course_id: str = Field(min_length=1)
    path: str = Field(min_length=1, max_length=500)
    kind: str = Field(min_length=1, max_length=80)
    size_bytes: int = Field(ge=0)


class CourseWorkspaceSetupInput(BaseModel):
    course_id: str | None = Field(default=None, max_length=120)
    course_title: str = Field(min_length=1, max_length=200)
    canvas_language: Literal["de", "en"] = "en"
    term: str | None = Field(default=None, max_length=80)
    lecture_title: str | None = Field(default=None, max_length=200)
    lecture_number: str | None = Field(default=None, max_length=20)
    lecture_count: int | None = Field(default=None, ge=1, le=80)
    lectures: list["LectureScheduleItem"] = Field(default_factory=list, max_length=80)
    replace_lectures: bool = False
    target: Literal["single-lecture", "full-course"] = "single-lecture"
    access_policy: CourseAccessPolicy = CourseAccessPolicy.TUEBINGEN_ENROLLED


class CourseWorkspaceResult(BaseModel):
    course: Course
    lectures: list[Lecture]
    active_lecture_id: str


class LectureScheduleItem(BaseModel):
    number: str = Field(min_length=1, max_length=20)
    title: str = Field(min_length=1, max_length=200)
    date: date
    material_path: str | None = Field(default=None, max_length=500)


class LectureScheduleProposal(BaseModel):
    course_id: str = Field(min_length=1)
    lectures: list[LectureScheduleItem]
    source_paths: list[str] = Field(default_factory=list)


class CanvasPublicationResult(BaseModel):
    course_id: str = Field(min_length=1)
    lecture_id: str = Field(min_length=1)
    published: bool
    version: int | None = Field(default=None, ge=1)
    published_at: str | None = Field(default=None, max_length=80)


class YoutubeDuration(BaseModel):
    iso8601: str | None = None
    seconds: int | None = Field(default=None, ge=0)
    display: str | None = Field(default=None, max_length=32)


class YoutubeVideoCandidate(BaseModel):
    video_id: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=200)
    channel_title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    url: str = Field(min_length=1, max_length=500)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    published_at: str | None = Field(default=None, max_length=80)
    view_count: int | None = Field(default=None, ge=0)
    duration: YoutubeDuration = Field(default_factory=YoutubeDuration)
    score: float = 0
    reason: str = Field(default="", max_length=500)


class YoutubeSearchResponse(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    items: list[YoutubeVideoCandidate]
    next_page_token: str | None = Field(default=None, max_length=200)


class YoutubeSelectionInput(BaseModel):
    section_id: str | None = Field(default=None, max_length=120)
    video: YoutubeVideoCandidate
    note: str | None = Field(default=None, max_length=500)


class YoutubeSelectionResult(BaseModel):
    course_id: str = Field(min_length=1)
    lecture_id: str = Field(min_length=1)
    section_id: str | None = None
    block_id: str = Field(min_length=1)
    video: YoutubeVideoCandidate


class CanvasState(BaseModel):
    focused_section_id: str | None = None
    active_artifact_id: str | None = None


class CanvasSectionPlacement(BaseModel):
    mode: Literal["after_section", "before_section"] = "after_section"
    section_id: str = Field(min_length=1, max_length=120)


class UserMemoryContext(BaseModel):
    global_notes: str = Field(default="", max_length=4000)
    course_notes: str = Field(default="", max_length=4000)
    preferences: dict[str, Any] = Field(default_factory=dict)


class AgentReadinessTask(BaseModel):
    id: str = Field(min_length=1, max_length=220)
    source_ref: str | None = Field(default=None, max_length=500)
    expected_evidence: str = Field(min_length=1, max_length=1000)
    scaffold_policy: TutorScaffoldPolicy


class AgentCoachingContext(BaseModel):
    session_goal: str = Field(default="", max_length=500)
    goal_is_new: bool = False
    prior_assistance: bool = False
    needs_evidence_count: int = Field(default=0, ge=0)
    last_gate_status: Literal["passed", "needs_evidence", "not_assessed"] | None = None
    delayed_transfer_due: bool = False
    support_before_attempt: bool = False
    last_assistance_level: AssistanceLevel = "none"
    evidence_ids: list[str] = Field(default_factory=list, max_length=40)
    missing_evidence_ids: list[str] = Field(default_factory=list, max_length=40)


class AgentTurnInput(BaseModel):
    user_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    lecture_id: str = Field(min_length=1)
    attendance: AttendanceStatus
    message: str = Field(min_length=1, max_length=4000)
    model: str | None = Field(default=None, min_length=3, max_length=200)
    canvas_state: CanvasState = Field(default_factory=CanvasState)
    canvas_context: CanvasDocument | None = None
    user_memory: UserMemoryContext = Field(default_factory=UserMemoryContext)
    readiness_task: AgentReadinessTask | None = None
    scaffold_policy: TutorScaffoldPolicy | None = None
    coaching_context: AgentCoachingContext = Field(default_factory=AgentCoachingContext)


class AgentTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    course_id: str = Field(min_length=1)
    lecture_id: str = Field(min_length=1)
    attendance: AttendanceStatus
    message: str = Field(min_length=1, max_length=4000)
    canvas_state: CanvasState = Field(default_factory=CanvasState)
    canvas_context: CanvasDocument | None = None
    user_memory: UserMemoryContext = Field(default_factory=UserMemoryContext)
    readiness_task: AgentReadinessTask | None = None

    def for_user(self, user_id: str) -> AgentTurnInput:
        return AgentTurnInput(user_id=user_id, model=None, **self.model_dump())


class CanvasCommand(BaseModel):
    type: Literal[
        "focus_section",
        "highlight_span",
        "open_artifact",
        "append_section",
        "update_section",
    ]
    section_id: str | None = None
    span_id: str | None = None
    highlight_text: str | None = Field(default=None, max_length=160)
    artifact_id: str | None = None
    section: CanvasSection | None = None
    placement: CanvasSectionPlacement | None = None


class ArtifactCommand(BaseModel):
    type: Literal["summary", "quiz", "code", "diagram"]
    title: str
    payload: dict[str, Any]


class AgentTurnResult(BaseModel):
    message: str
    session_goal: str | None = Field(default=None, max_length=500)
    canvas_commands: list[CanvasCommand] = Field(default_factory=list)
    artifacts: list[ArtifactCommand] = Field(default_factory=list)
    quality_gate: QualityGateDecision | None = None
    model: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProviderSettings(BaseModel):
    provider: str
    model: str
    api_key_env: str
    capabilities: set[ProviderCapability]
