"""Reviewed parallel tasks and bounded arithmetic consistency, never executable code."""

from typing import Annotated, Literal
import math

from pydantic import BeforeValidator, Field, model_validator

from lecturepilot.course_practice_design_contract import (
    NonblankText,
    StrictPracticeDesignModel,
    freeze_collection,
)
from lecturepilot.course_practice_design_evidence import PracticeSourceAnchor

BoundedNumber = Annotated[float, Field(ge=-1e12, le=1e12, allow_inf_nan=False)]


class NumericConsistencyAssertion(StrictPracticeDesignModel):
    operation: Literal["add", "subtract", "multiply", "divide"]
    operands: Annotated[tuple[BoundedNumber, ...], BeforeValidator(freeze_collection)] = Field(
        min_length=2, max_length=2
    )
    expected: BoundedNumber
    tolerance: float = Field(default=1e-9, ge=0, le=1e-3, allow_inf_nan=False)

    @model_validator(mode="after")
    def check_consistency(self):
        left, right = self.operands
        if self.operation == "divide" and right == 0:
            raise ValueError("Numerical consistency assertion divides by zero.")
        result = {
            "add": lambda: left + right,
            "subtract": lambda: left - right,
            "multiply": lambda: left * right,
            "divide": lambda: left / right,
        }[self.operation]()
        if not math.isclose(result, self.expected, rel_tol=0, abs_tol=self.tolerance):
            raise ValueError("Numerical consistency assertion failed.")
        return self


class SupplementalPracticeTask(StrictPracticeDesignModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")
    stage: Literal["independent_exit", "delayed_transfer"]
    prompt: NonblankText = Field(max_length=2_000)
    source_anchor: PracticeSourceAnchor
    surface_change: NonblankText = Field(max_length=1_000)
    numeric_assertions: Annotated[
        tuple[NumericConsistencyAssertion, ...], BeforeValidator(freeze_collection)
    ] = Field(default_factory=tuple, max_length=8)

    @model_validator(mode="after")
    def reserve_canonical_ids(self):
        if self.id in {"baseline", "independent-exit", "delayed-transfer"}:
            raise ValueError("Supplemental task IDs cannot replace canonical tasks.")
        return self
