from datetime import date

from lecturepilot.lecture_schedule_planner import LectureSchedulePlanner
from lecturepilot.providers import ProviderRegistry
from lecturepilot.source_bundle import SourceBundleFile


async def test_schedule_planner_keeps_model_paths_for_noncanonical_pdf_names(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    source = tmp_path / "12454__WBIII_OOP+Mocking.pdf"
    source.write_bytes(b"%PDF-1.7\n")
    planner = LectureSchedulePlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=_NoncanonicalPdfScheduleClient(),
    )

    proposal = await planner.propose_schedule(
        course_id="software-quality",
        files=[SourceBundleFile(path=source.name, kind="pdf", size_bytes=source.stat().st_size)],
        roots=[tmp_path],
        first_lecture_date=date(2026, 4, 14),
        requested_count=5,
    )

    fifth = proposal.lectures[4]
    assert fifth.title == "White Box III"
    assert fifth.date == date(2026, 5, 12)
    assert fifth.material_path == source.name


class _NoncanonicalPdfScheduleClient:
    async def complete_schedule(self, *, settings, messages):
        return {
            "lectures": [
                {
                    "number": "05",
                    "title": "White Box III",
                    "date": "2026-05-12",
                    "material_path": "12454__WBIII_OOP+Mocking.pdf",
                }
            ]
        }
