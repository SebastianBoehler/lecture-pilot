from __future__ import annotations

from typing import Annotated, Literal, get_args

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def _normalize_nonblank_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    if not normalized:
        raise ValueError("Required text cannot be blank.")
    return normalized


def _freeze_collection(value: object) -> object:
    return tuple(value) if isinstance(value, list) else value


NonblankText = Annotated[str, BeforeValidator(_normalize_nonblank_text)]
PlanningContextField = Literal[
    "learner_level",
    "prerequisites",
    "time_budget_minutes",
    "allowed_aids",
    "assessment_conditions",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, revalidate_instances="always", strict=True
    )


class PracticePlanningInsufficiency(_StrictModel):
    field: PlanningContextField
    description: NonblankText = Field(
        min_length=1,
        max_length=1_000,
        description="Why the supplied source cannot support this planning-context value.",
    )


class PracticePlanningContext(_StrictModel):
    learner_level: NonblankText | None = Field(
        description="Professor-editable source-supported learner level, or null if unsupported."
    )
    prerequisites: Annotated[
        tuple[NonblankText, ...] | None, BeforeValidator(_freeze_collection)
    ] = Field(max_length=40, description="Known prerequisites, or null if the source is silent.")
    time_budget_minutes: int | None = Field(
        ge=1, description="Available learner time in minutes, or null if the source is silent."
    )
    allowed_aids: Annotated[
        tuple[NonblankText, ...] | None, BeforeValidator(_freeze_collection)
    ] = Field(max_length=40, description="Explicitly allowed aids, or null if unsupported.")
    assessment_conditions: NonblankText | None = Field(
        description="Professor-editable assessment conditions, or null if unsupported."
    )
    insufficiencies: Annotated[
        tuple[PracticePlanningInsufficiency, ...], BeforeValidator(_freeze_collection)
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
