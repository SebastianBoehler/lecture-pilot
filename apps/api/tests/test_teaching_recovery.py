import asyncio
import json

import pytest

from lecturepilot.authoring.authoring_limits import (
    AuthoringBudgetExceeded,
    current_authoring_budget,
)
from lecturepilot.llm.model_client import ModelExecutionError
from lecturepilot.learning_design.teaching_design_runtime import run_implementation_repair


@pytest.mark.parametrize("failure", ["timeout", "deadline", "tokens"])
async def test_saved_implementation_continues_without_replacing_owned_arguments(
    tmp_path, monkeypatch, failure
):
    import lecturepilot.learning_design.teaching_design_runtime as runtime

    calls = []
    budgets = []
    authorize_calls = []
    args = dict(root=tmp_path, authorize=lambda: authorize_calls.append(True))

    async def run(**kwargs):
        calls.append(kwargs)
        budgets.append(current_authoring_budget())
        if len(calls) == 1:
            path = tmp_path / "identity" / "draft.json"
            path.parent.mkdir()
            path.write_text(json.dumps({"targets": {"g1": {"teaching": "saved"}}}))
            if failure == "timeout":
                try:
                    raise TimeoutError()
                except TimeoutError as exc:
                    raise ModelExecutionError("Provider timeout") from exc
            raise AuthoringBudgetExceeded("deadline" if failure == "deadline" else "tokens")
        return "accepted"

    monkeypatch.setattr(runtime, "_run_implementation_repair", run)
    assert await run_implementation_repair(**args) == "accepted"
    assert calls == [args, args]
    assert budgets[0] is not budgets[1]
    assert len(authorize_calls) >= 2


async def test_no_progress_budget_failure_is_not_repeated(tmp_path, monkeypatch):
    import lecturepilot.learning_design.teaching_design_runtime as runtime

    calls = []

    async def run(**kwargs):
        calls.append(True)
        raise AuthoringBudgetExceeded("tokens")

    monkeypatch.setattr(runtime, "_run_implementation_repair", run)
    with pytest.raises(AuthoringBudgetExceeded):
        await run_implementation_repair(root=tmp_path, authorize=lambda: None)
    assert len(calls) == 1


async def test_provider_failure_has_bounded_continuation(tmp_path, monkeypatch):
    import lecturepilot.learning_design.teaching_design_runtime as runtime

    calls = []

    async def run(**kwargs):
        calls.append(True)
        try:
            raise TimeoutError()
        except TimeoutError as exc:
            raise ModelExecutionError("timeout") from exc

    monkeypatch.setattr(runtime, "_run_implementation_repair", run)
    with pytest.raises(ModelExecutionError):
        await run_implementation_repair(root=tmp_path, authorize=lambda: None)
    assert len(calls) == 3


@pytest.mark.parametrize("error", [ValueError("changed identity"), asyncio.CancelledError()])
async def test_ownership_and_cancellation_are_never_retried(tmp_path, monkeypatch, error):
    import lecturepilot.learning_design.teaching_design_runtime as runtime

    calls = []

    async def run(**kwargs):
        calls.append(True)
        raise error

    monkeypatch.setattr(runtime, "_run_implementation_repair", run)
    with pytest.raises(type(error)):
        await run_implementation_repair(root=tmp_path, authorize=lambda: None)
    assert len(calls) == 1


async def test_scope_conflict_is_not_retried_even_with_saved_progress(tmp_path, monkeypatch):
    import lecturepilot.learning_design.teaching_design_runtime as runtime
    from lecturepilot.authoring.authoring_models import AuthoringDesignConflict

    calls = []

    async def run(**kwargs):
        calls.append(True)
        path = tmp_path / "identity" / "draft.json"
        path.parent.mkdir()
        path.write_text(json.dumps({"targets": {"g1": "saved"}}))
        raise AuthoringDesignConflict("Approved goal unsupported")

    monkeypatch.setattr(runtime, "_run_implementation_repair", run)
    with pytest.raises(AuthoringDesignConflict):
        await run_implementation_repair(root=tmp_path, authorize=lambda: None)
    assert len(calls) == 1


async def test_real_deadline_continues_saved_targets(tmp_path, monkeypatch):
    import lecturepilot.learning_design.teaching_design_runtime as runtime
    import lecturepilot.learning_design.teaching_recovery as recovery

    calls = []

    async def run(**kwargs):
        calls.append(True)
        if len(calls) == 1:
            path = tmp_path / "identity" / "draft.json"
            path.parent.mkdir()
            path.write_text(json.dumps({"targets": {"g1": "saved"}}))
            await asyncio.Event().wait()
        return "accepted"

    monkeypatch.setattr(runtime, "_run_implementation_repair", run)
    monkeypatch.setattr(recovery, "AUTHORING_DEADLINE_SECONDS", 0.01)
    assert await run_implementation_repair(root=tmp_path, authorize=lambda: None) == "accepted"
    assert len(calls) == 2


async def test_progress_does_not_remove_the_attempt_limit(tmp_path, monkeypatch):
    import lecturepilot.learning_design.teaching_design_runtime as runtime

    calls = []

    async def run(**kwargs):
        calls.append(True)
        path = tmp_path / "identity" / "draft.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"targets": {"g1": len(calls)}}))
        raise AuthoringBudgetExceeded("tokens")

    monkeypatch.setattr(runtime, "_run_implementation_repair", run)
    with pytest.raises(AuthoringBudgetExceeded):
        await run_implementation_repair(root=tmp_path, authorize=lambda: None)
    assert len(calls) == 3
