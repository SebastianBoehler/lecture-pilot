from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict


def normalize_nonblank_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    if not normalized:
        raise ValueError("Required text cannot be blank.")
    return normalized


def freeze_collection(value: object) -> object:
    return tuple(value) if isinstance(value, list) else value


NonblankText = Annotated[str, BeforeValidator(normalize_nonblank_text)]


class StrictPracticeDesignModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, revalidate_instances="always", strict=True
    )


def require_observable_outcome(outcome: str) -> None:
    normalized = outcome.strip().casefold()
    if normalized in {"understand", "know"} or normalized.startswith(("understand ", "know ")):
        raise ValueError("Practice target outcomes must be observable independent capabilities.")
