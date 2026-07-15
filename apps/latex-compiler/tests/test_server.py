from __future__ import annotations

from http.client import HTTPConnection
import json
import logging
from pathlib import Path
from threading import Event, Thread
import time
import zipfile

import pytest

from lecturepilot_latex_compiler.errors import COMPILE_FAILED, CompilerServiceError
from lecturepilot_latex_compiler.request_diagnostics import (
    LOGGER_NAME,
    configure_logging,
)
from lecturepilot_latex_compiler.server import create_server


def _zip_bytes(tmp_path: Path) -> bytes:
    path = tmp_path / "source.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("main.tex", "content")
    return path.read_bytes()


def _perform_request(
    server, method: str, target: str, body: bytes = b"", headers: dict | None = None
):
    connection = HTTPConnection(*server.server_address, timeout=3)
    connection.request(method, target, body=body, headers=headers or {})
    response = connection.getresponse()
    payload = response.read()
    request_id = response.getheader("X-Request-ID")
    connection.close()
    return response.status, response.getheader("Content-Type"), payload, request_id


def _request(
    server, method: str, target: str, body: bytes = b"", headers: dict | None = None
):
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    result = _perform_request(server, method, target, body, headers)
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)
    return result


def test_compile_endpoint_accepts_raw_zip(tmp_path: Path) -> None:
    seen = {}

    def compile_source(path: Path, main_path: str) -> bytes:
        seen["archive"] = path.read_bytes()
        seen["main_path"] = main_path
        return b"%PDF-1.7\ncompiled"

    server = create_server("127.0.0.1", 0, compile_function=compile_source)
    body = _zip_bytes(tmp_path)
    status, content_type, response, request_id = _request(
        server,
        "POST",
        "/compile?main_path=main.tex",
        body,
        {
            "Content-Type": "application/zip",
            "Content-Length": str(len(body)),
            "X-Request-ID": "course-run_123",
        },
    )

    assert (status, content_type, response) == (
        200,
        "application/pdf",
        b"%PDF-1.7\ncompiled",
    )
    assert request_id == "course-run_123"
    assert seen == {"archive": body, "main_path": "main.tex"}


def test_compile_endpoint_returns_sanitized_error(tmp_path: Path) -> None:
    def fail(_path: Path, _main_path: str) -> bytes:
        raise CompilerServiceError("compile_failed", COMPILE_FAILED)

    server = create_server("127.0.0.1", 0, compile_function=fail)
    body = _zip_bytes(tmp_path)
    status, _, response, _ = _request(
        server,
        "POST",
        "/compile?main_path=main.tex",
        body,
        {"Content-Type": "application/zip", "Content-Length": str(len(body))},
    )

    payload = json.loads(response)
    assert status == 422
    assert payload["error"] == {"code": "compile_failed", "message": COMPILE_FAILED}


def test_compile_endpoint_sanitizes_unexpected_error(tmp_path: Path) -> None:
    def fail(_path: Path, _main_path: str) -> bytes:
        raise RuntimeError("private course text")

    server = create_server("127.0.0.1", 0, compile_function=fail)
    body = _zip_bytes(tmp_path)
    status, _, response, _ = _request(
        server,
        "POST",
        "/compile?main_path=main.tex",
        body,
        {"Content-Type": "application/zip", "Content-Length": str(len(body))},
    )

    payload = json.loads(response)
    assert status == 500
    assert payload["error"] == {
        "code": "internal_error",
        "message": "LaTeX slide rendering failed safely.",
    }


def test_three_concurrent_compiles_queue_and_succeed(tmp_path: Path) -> None:
    first_started = Event()
    release_first = Event()
    calls = 0

    def compile_source(_path: Path, _main_path: str) -> bytes:
        nonlocal calls
        calls += 1
        if calls == 1:
            first_started.set()
            assert release_first.wait(timeout=2)
        return b"%PDF-1.7\ncompiled"

    server = create_server("127.0.0.1", 0, compile_function=compile_source)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    body = _zip_bytes(tmp_path)
    headers = {"Content-Type": "application/zip", "Content-Length": str(len(body))}
    results = []

    workers = [
        Thread(
            target=lambda: results.append(
                _perform_request(
                    server, "POST", "/compile?main_path=main.tex", body, headers
                )
            )
        )
        for _ in range(3)
    ]
    first, *waiting = workers
    first.start()
    assert first_started.wait(timeout=1)
    for worker in waiting:
        worker.start()
    time.sleep(0.1)
    assert all(worker.is_alive() for worker in waiting)
    release_first.set()
    for worker in workers:
        worker.join(timeout=2)
    server.shutdown()
    server.server_close()
    server_thread.join(timeout=2)

    assert calls == 3
    assert sorted(result[0] for result in results) == [200, 200, 200]


def test_request_log_is_metadata_only_and_replaces_unsafe_id(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    def fail(_path: Path, _main_path: str) -> bytes:
        raise RuntimeError("private course text")

    server = create_server("127.0.0.1", 0, compile_function=fail)
    body = _zip_bytes(tmp_path)
    with caplog.at_level("INFO", logger=LOGGER_NAME):
        status, _, _, request_id = _request(
            server,
            "POST",
            "/compile?main_path=private-course-name.tex",
            body,
            {
                "Content-Type": "application/zip",
                "Content-Length": str(len(body)),
                "X-Request-ID": "unsafe id with spaces",
            },
        )

    assert status == 500
    assert request_id and request_id != "unsafe id with spaces"
    assert len(caplog.messages) == 1
    event = json.loads(caplog.messages[0])
    assert event == {
        "code": "internal_error",
        "event": "latex_compile_request",
        "exception_type": "RuntimeError",
        "latency_ms": event["latency_ms"],
        "request_id": request_id,
        "status": 500,
    }
    assert isinstance(event["latency_ms"], int)
    assert "private" not in caplog.messages[0]


def test_compiler_metadata_log_rotates_for_fourteen_calendar_files(
    tmp_path: Path, monkeypatch
) -> None:
    path = tmp_path / "compiler.jsonl"
    monkeypatch.setenv("LECTUREPILOT_METADATA_LOG_PATH", str(path))

    configure_logging()

    logger = logging.getLogger(LOGGER_NAME)
    handler = next(
        item
        for item in logger.handlers
        if getattr(item, "lecturepilot_log_path", None) == str(path)
    )
    assert handler.backupCount == 13
    assert logger.propagate is False
    logger.removeHandler(handler)
    handler.close()
    logger.propagate = True
