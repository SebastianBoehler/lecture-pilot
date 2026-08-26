from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, model_validator

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_practice_design_contract import (
    NonblankText,
    StrictPracticeDesignModel,
    freeze_collection,
)


class PracticeDesignBenchmarkFixture(StrictPracticeDesignModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")
    discipline: NonblankText = Field(max_length=80)
    domain: Literal["conceptual", "quantitative"]
    provenance: Literal["synthetic", "public"]
    allowed_source_paths: Annotated[tuple[str, ...], BeforeValidator(freeze_collection)] = Field(
        min_length=1, max_length=8
    )
    source: CanvasDocument

    @model_validator(mode="after")
    def require_exact_source_routes(self) -> PracticeDesignBenchmarkFixture:
        if len(set(self.allowed_source_paths)) != len(self.allowed_source_paths):
            raise ValueError("Benchmark source paths must be unique.")
        section_paths = {section.source_ref for section in self.source.sections}
        if None in section_paths or section_paths != set(self.allowed_source_paths):
            raise ValueError("Every fixture section must use one exact allowed source path.")
        return self

    @property
    def source_revision(self) -> str:
        payload = {
            "allowed_source_paths": self.allowed_source_paths,
            "source": self.source.model_dump(mode="json"),
        }
        canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()


class _FixtureCorpus(StrictPracticeDesignModel):
    schema_version: Literal[1]
    fixtures: Annotated[
        tuple[PracticeDesignBenchmarkFixture, ...], BeforeValidator(freeze_collection)
    ] = Field(min_length=2, max_length=20)

    @model_validator(mode="after")
    def require_multi_discipline_domains(self) -> _FixtureCorpus:
        if {fixture.domain for fixture in self.fixtures} != {"conceptual", "quantitative"}:
            raise ValueError("Benchmark fixtures must span conceptual and quantitative domains.")
        if len({fixture.discipline for fixture in self.fixtures}) < 3:
            raise ValueError("Benchmark fixtures must span at least three disciplines.")
        return self


def load_practice_design_benchmark_fixtures(
    path: Path,
) -> tuple[PracticeDesignBenchmarkFixture, ...]:
    corpus = _FixtureCorpus.model_validate_json(path.read_text(encoding="utf-8"))
    fixture_ids = tuple(fixture.id for fixture in corpus.fixtures)
    if fixture_ids != tuple(sorted(fixture_ids)) or len(set(fixture_ids)) != len(fixture_ids):
        raise ValueError("Benchmark fixtures must have unique IDs in sorted order.")
    return corpus.fixtures
