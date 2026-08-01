from __future__ import annotations

import time
import os

import lecturepilot.bounded_processing as bounded_processing


def _burn_cpu(seconds: float) -> tuple[int, float]:
    started = time.process_time()
    while time.process_time() - started < seconds:
        pass
    return os.getpid(), time.process_time() - started


def test_each_bounded_task_gets_its_own_cpu_budget(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_BOUNDED_PROCESSING", "true")
    monkeypatch.setenv("LECTUREPILOT_PROCESSING_WORKERS", "1")
    monkeypatch.setenv("LECTUREPILOT_PROCESSING_CPU_SECONDS", "1")
    monkeypatch.setenv("LECTUREPILOT_PROCESSING_TIMEOUT_SECONDS", "5")
    bounded_processing._executor = None

    try:
        first = bounded_processing.run_bounded(_burn_cpu, 0.75)
        second = bounded_processing.run_bounded(_burn_cpu, 0.75)
    finally:
        executor = bounded_processing._executor
        bounded_processing._executor = None
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)

    assert first[1] >= 0.75
    assert second[1] >= 0.75
    assert first[0] != second[0]
