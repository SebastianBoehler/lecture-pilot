from datetime import date

import pytest

from lecturepilot.lecture_schedule_planner import (
    LiteLLMScheduleClient,
    _read_proposal,
    _source_evidence,
)
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import ProviderCapability, ProviderSettings
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.source_bundle import SourceBundleFile


def test_schedule_agent_receives_complete_inventory_without_regex_seed() -> None:
    files = [
        SourceBundleFile(
            path=f"uploads/nlp/{number}_Topic_{number}.pdf",
            kind="pdf",
            size_bytes=10_000_000 - number,
        )
        for number in range(1, 13)
    ]
    files.extend(
        SourceBundleFile(
            path=f"uploads/nlp/tmp/generated/derived-{number:03d}.txt",
            kind="text",
            size_bytes=100 + number,
        )
        for number in range(90)
    )
    files.append(
        SourceBundleFile(
            path="uploads/nlp/Lecture_2_Video.mp4",
            kind="video",
            size_bytes=70_000_000,
        )
    )

    evidence = _source_evidence(
        "nlp",
        files,
        [],
        first_lecture_date=date(2026, 4, 13),
        requested_count=None,
    )

    assert "Deterministic file candidates" not in evidence
    assert "Complete source inventory (103 files)" in evidence
    for number in range(1, 13):
        assert f"uploads/nlp/{number}_Topic_{number}.pdf" in evidence


def test_schedule_contract_rejects_unknown_material_path() -> None:
    files = [SourceBundleFile(path="known.pdf", kind="pdf", size_bytes=1)]

    with pytest.raises(ProviderConfigurationError, match="listed source path"):
        _read_proposal(
            {
                "lectures": [
                    {
                        "number": "01",
                        "title": "Introduction",
                        "date": "2026-04-13",
                        "material_path": "invented.pdf",
                    }
                ]
            },
            "nlp",
            files,
        )


def test_schedule_contract_rejects_duplicate_lecture_numbers() -> None:
    files = [
        SourceBundleFile(path="one.pdf", kind="pdf", size_bytes=1),
        SourceBundleFile(path="two.pdf", kind="pdf", size_bytes=1),
    ]

    with pytest.raises(ProviderConfigurationError, match="unique lecture number"):
        _read_proposal(
            {
                "lectures": [
                    {
                        "number": "01",
                        "title": "Introduction",
                        "date": "2026-04-13",
                        "material_path": "one.pdf",
                    },
                    {
                        "number": "1",
                        "title": "Language models",
                        "date": "2026-04-20",
                        "material_path": "two.pdf",
                    },
                ]
            },
            "nlp",
            files,
        )


@pytest.mark.asyncio
async def test_schedule_client_reports_exhausted_provider_credits(monkeypatch) -> None:
    async def completion(**_kwargs):
        raise _QuotaError(
            "You have no credits remaining.",
            code="credit_balance_exhausted",
        )

    monkeypatch.setattr("litellm.acompletion", completion)
    settings = ProviderSettings(
        provider="openai",
        model="openai/gpt-5.6-luna",
        api_key_env="OPENAI_API_KEY",
        capabilities={ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON},
    )

    with pytest.raises(
        ModelExecutionError,
        match=(
            "OpenAI API credits are exhausted. Add credits to the configured "
            "provider account, then retry this request."
        ),
    ):
        await LiteLLMScheduleClient().complete_schedule(settings=settings, messages=[])


class _QuotaError(RuntimeError):
    status_code = 429

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code
