from datetime import date

import pytest

from lecturepilot.lecture_schedule_planner import LectureSchedulePlanner
from lecturepilot.providers import ProviderRegistry
from lecturepilot.source_bundle import SourceBundleFile


@pytest.mark.asyncio
async def test_schedule_restores_missing_numbered_sources_from_shuffled_model_rows(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    files = []
    for number in range(1, 4):
        source = tmp_path / f"Lecture{number:02d}-eng.tex"
        source.write_text(rf"\section{{Topic {number}}}", encoding="utf-8")
        files.append(
            SourceBundleFile(path=source.name, kind="latex", size_bytes=source.stat().st_size)
        )
    planner = LectureSchedulePlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=_ShuffledScheduleClient(),
    )

    proposal = await planner.propose_schedule(
        course_id="gml",
        files=files,
        roots=[tmp_path],
        first_lecture_date=date(2026, 4, 15),
        requested_count=3,
    )

    assert [lecture.number for lecture in proposal.lectures] == ["01", "02", "03"]
    assert [lecture.material_path for lecture in proposal.lectures] == [
        "Lecture01-eng.tex",
        "Lecture02-eng.tex",
        "Lecture03-eng.tex",
    ]
    assert proposal.lectures[2].title == "Model topic 3"


class _ShuffledScheduleClient:
    async def complete_schedule(self, *, settings, messages):
        return {
            "lectures": [
                {
                    "number": "01",
                    "title": "Model topic 3",
                    "date": "2026-04-15",
                    "material_path": "Lecture03-eng.tex",
                },
                {
                    "number": "02",
                    "title": "Model topic 2",
                    "date": "2026-04-22",
                    "material_path": "Lecture02-eng.tex",
                },
                {
                    "number": "03",
                    "title": "Model topic 3",
                    "date": "2026-04-29",
                    "material_path": "Lecture03-eng.tex",
                },
            ]
        }
