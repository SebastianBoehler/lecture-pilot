from __future__ import annotations

from pydantic import Field

from lecturepilot.course_learning_intent import has_approved_intent

from lecturepilot.course_practice_design_contract import StrictPracticeDesignModel
from lecturepilot.course_practice_design_models import PracticeDesign

_REVISION_PATTERN = r"^[a-f0-9]{64}$"


class PracticeDesignReadiness(StrictPracticeDesignModel):
    lecture_id: str = Field(min_length=1, max_length=120)
    current_source_revision: str = Field(pattern=_REVISION_PATTERN)
    practice_design_revision: str | None = Field(default=None, pattern=_REVISION_PATTERN)
    ready_for_generation: bool

    @classmethod
    def current(
        cls,
        *,
        lecture_id: str,
        source_revision: str,
        design: PracticeDesign | None,
    ) -> "PracticeDesignReadiness":
        approval = design.approval if design is not None else None
        ready = bool(
            design
            and design.source_revision == source_revision
            and (
                (approval is None and has_approved_intent(design))
                or (
                    approval
                    and approval.source_revision == source_revision
                    and approval.practice_design_revision == design.revision
                )
            )
        )
        return cls(
            lecture_id=lecture_id,
            current_source_revision=source_revision,
            practice_design_revision=design.revision if design is not None else None,
            ready_for_generation=ready,
        )
