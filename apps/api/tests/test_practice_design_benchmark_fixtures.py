from pathlib import Path

from lecturepilot.course_practice_design_benchmark_fixtures import (
    load_practice_design_benchmark_fixtures,
)


ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = ROOT / "benchmarks/practice-design/fixtures.json"


def test_frozen_benchmark_fixtures_span_distinct_domains_with_stable_revisions() -> None:
    fixtures = load_practice_design_benchmark_fixtures(FIXTURE_PATH)

    assert tuple(fixture.id for fixture in fixtures) == (
        "biology-natural-selection",
        "history-source-corroboration",
        "physics-constant-acceleration",
        "statistics-conditional-probability",
    )
    assert {fixture.domain for fixture in fixtures} == {"conceptual", "quantitative"}
    assert len({fixture.discipline for fixture in fixtures}) == 4
    assert {fixture.provenance for fixture in fixtures} == {"synthetic"}
    assert {fixture.id: fixture.source_revision for fixture in fixtures} == {
        "biology-natural-selection": (
            "cab8585d1b38b524d3f4ef84c4ee7b8c34313030fa393c6a60ae214c9f9f6a48"
        ),
        "history-source-corroboration": (
            "d9134603dd38adf30486dbbab8a3e7dc7de9cb71bc6818a9ebd27e429b88e60c"
        ),
        "physics-constant-acceleration": (
            "4dc25dcb87658f7480a284a66646d14792f6797f8c1f9defc0f9c1f449602d11"
        ),
        "statistics-conditional-probability": (
            "ec39cf6adea66edb3a6e4157295096603e50a63bbf849859cfeb1c0b2627da79"
        ),
    }
    assert all(
        set(fixture.allowed_source_paths)
        == {section.source_ref for section in fixture.source.sections}
        for fixture in fixtures
    )
