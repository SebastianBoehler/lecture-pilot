from __future__ import annotations

from typing import Annotated, Literal, get_args

from pydantic import BeforeValidator, Field, model_validator

from lecturepilot.course_practice_design_contract import (
    NonblankText,
    StrictPracticeDesignModel,
    freeze_collection,
)


PlanningContextField = Literal[
    "learner_level",
    "prerequisites",
    "time_budget_minutes",
    "allowed_aids",
    "assessment_conditions",
]


class PracticePlanningInsufficiency(StrictPracticeDesignModel):
    field: PlanningContextField
    description: NonblankText = Field(
        min_length=1,
        max_length=1_000,
        description="Why the supplied source cannot support this planning-context value.",
    )


class PracticePlanningContext(StrictPracticeDesignModel):
    learner_level: NonblankText | None = Field(
        description="Professor-editable source-supported learner level, or null if unsupported."
    )
    prerequisites: Annotated[
        tuple[NonblankText, ...] | None, BeforeValidator(freeze_collection)
    ] = Field(max_length=40, description="Known prerequisites, or null if the source is silent.")
    time_budget_minutes: int | None = Field(
        ge=1, description="Available learner time in minutes, or null if the source is silent."
    )
    allowed_aids: Annotated[tuple[NonblankText, ...] | None, BeforeValidator(freeze_collection)] = (
        Field(max_length=40, description="Explicitly allowed aids, or null if unsupported.")
    )
    assessment_conditions: NonblankText | None = Field(
        description="Professor-editable assessment conditions, or null if unsupported."
    )
    insufficiencies: Annotated[
        tuple[PracticePlanningInsufficiency, ...], BeforeValidator(freeze_collection)
    ] = Field(
        max_length=5,
        description="Exactly one explicit source insufficiency for every null context field.",
    )

    @model_validator(mode="after")
    def validate_insufficiencies(self) -> PracticePlanningContext:
        fields = tuple(item.field for item in self.insufficiencies)
        missing = {
            field for field in get_args(PlanningContextField) if getattr(self, field) is None
        }
        if len(fields) != len(set(fields)) or set(fields) != missing:
            raise ValueError(
                "Planning context needs exactly one explicit insufficiency for every missing field."
            )
        return self
