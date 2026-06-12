import json
import sys
from datetime import date
from types import SimpleNamespace

from lecturepilot.lecture_schedule_planner import LectureSchedulePlanner, LiteLLMScheduleClient
from lecturepilot.providers import ProviderConfigurationError, ProviderRegistry
from lecturepilot.source_bundle import SourceBundleFile


async def test_litellm_schedule_client_requests_schedule_schema(monkeypatch) -> None:
    calls = []
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"lectures": []})))]
        )

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))

    payload = await LiteLLMScheduleClient().complete_schedule(
        settings=ProviderRegistry.from_env("gemini/test-model").require_ready([]),
        messages=[{"role": "user", "content": "Schedule"}],
    )

    assert payload == {"lectures": []}
    assert calls[0]["response_format"]["type"] == "json_schema"
    schema = calls[0]["response_format"]["json_schema"]["schema"]
    assert calls[0]["response_format"]["json_schema"]["strict"] is True
    assert schema["required"] == ["lectures"]


async def test_schedule_planner_sends_topic_outline_to_model(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    source = tmp_path / "Lecture03-eng.tex"
    source.write_text(
        r"""
        \begin{frame}{Plan}Housekeeping\end{frame}
        \section{Bayesian Decision Theory}
        \begin{frame}{Bayes Rule}
        Posterior probabilities combine prior, likelihood and evidence.
        \end{frame}
        \section{Losses, Risks and Discriminant Functions}
        """,
        encoding="utf-8",
    )
    client = _FakeScheduleClient()
    planner = LectureSchedulePlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=client,
    )

    proposal = await planner.propose_schedule(
        course_id="martius-ml",
        files=[SourceBundleFile(path="Lecture03-eng.tex", kind="latex", size_bytes=source.stat().st_size)],
        roots=[tmp_path],
        first_lecture_date=date(2026, 5, 6),
        requested_count=None,
    )

    assert proposal.lectures[0].title == "Bayesian Decision Theory"
    assert "Bayesian Decision Theory" in client.last_messages[1]["content"]
    assert "Losses, Risks and Discriminant Functions" in client.last_messages[1]["content"]


async def test_schedule_planner_repairs_non_object_model_response(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    source = tmp_path / "Lecture01.tex"
    source.write_text(r"\section{Introduction}", encoding="utf-8")
    client = _RepairingScheduleClient()
    planner = LectureSchedulePlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=client,
    )

    proposal = await planner.propose_schedule(
        course_id="demo-course",
        files=[SourceBundleFile(path="Lecture01.tex", kind="latex", size_bytes=source.stat().st_size)],
        roots=[tmp_path],
        first_lecture_date=date(2026, 5, 6),
        requested_count=None,
    )

    assert proposal.lectures[0].title == "Introduction"
    assert client.calls == 2
    assert "Do not return a bare array" in client.last_messages[-1]["content"]


class _FakeScheduleClient:
    def __init__(self) -> None:
        self.last_messages = []

    async def complete_schedule(self, *, settings, messages):
        assert settings.model == "gemini/test-model"
        self.last_messages = messages
        return {
            "lectures": [
                {
                    "number": "03",
                    "title": "Bayesian Decision Theory",
                    "date": "2026-05-06",
                    "material_path": "Lecture03-eng.tex",
                }
            ]
        }


class _RepairingScheduleClient:
    def __init__(self) -> None:
        self.calls = 0
        self.last_messages = []

    async def complete_schedule(self, *, settings, messages):
        self.calls += 1
        self.last_messages = messages
        if self.calls == 1:
            raise ProviderConfigurationError("Course planner JSON must be an object.")
        return {
            "lectures": [
                {
                    "number": "01",
                    "title": "Introduction",
                    "date": "2026-05-06",
                    "material_path": "Lecture01.tex",
                }
            ]
        }
