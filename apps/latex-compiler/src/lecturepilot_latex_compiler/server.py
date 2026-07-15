from __future__ import annotations

from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from threading import BoundedSemaphore
from urllib.parse import parse_qs, urlsplit

from lecturepilot_latex_compiler.compiler import compile_archive
from lecturepilot_latex_compiler.errors import INVALID_REQUEST, CompilerServiceError
from lecturepilot_latex_compiler.limits import COMPILE_QUEUE_SECONDS, MAX_ARCHIVE_BYTES
from lecturepilot_latex_compiler.request_diagnostics import (
    RequestDiagnostics,
    configure_logging,
    safe_request_id,
)


CompileFunction = Callable[[Path, str], bytes]


class CompilerHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self, address: tuple[str, int], compile_function: CompileFunction
    ) -> None:
        super().__init__(address, CompilerRequestHandler)
        self.compile_function = compile_function
        self.compile_slot = BoundedSemaphore(1)


class CompilerRequestHandler(BaseHTTPRequestHandler):
    server: CompilerHTTPServer
    server_version = "LecturePilotCompiler"
    sys_version = ""

    def do_GET(self) -> None:
        if urlsplit(self.path).path != "/health":
            self._json_error(404, "not_found", "Not found.")
            return
        self._write_json(200, {"status": "ok"})

    def do_POST(self) -> None:
        self.request_diagnostics = RequestDiagnostics(
            safe_request_id(self.headers.get("X-Request-ID"))
        )
        try:
            self._handle_compile_request()
        except (BrokenPipeError, ConnectionResetError):
            self.request_diagnostics.record(499, "client_disconnected")
        except Exception as exc:
            self.request_diagnostics.record_exception(exc)
            try:
                self._json_error(
                    500,
                    "internal_error",
                    "LaTeX slide rendering failed safely.",
                )
            except OSError:
                self.request_diagnostics.record(499, "client_disconnected")
        finally:
            self.request_diagnostics.emit()

    def _handle_compile_request(self) -> None:
        url = urlsplit(self.path)
        if url.path != "/compile":
            self._json_error(404, "not_found", "Not found.")
            return
        query = parse_qs(url.query, keep_blank_values=True)
        main_paths = query.get("main_path", [])
        if len(main_paths) != 1 or not main_paths[0]:
            self._json_error(400, "invalid_request", INVALID_REQUEST)
            return
        if self.headers.get_content_type() != "application/zip":
            self._json_error(415, "invalid_request", INVALID_REQUEST)
            return
        length = self._content_length()
        if length is None:
            return
        if not self.server.compile_slot.acquire(timeout=COMPILE_QUEUE_SECONDS):
            self.close_connection = True
            self._json_error(
                503, "compiler_busy", "LaTeX slide rendering is busy. Retry shortly."
            )
            return
        try:
            with tempfile.NamedTemporaryFile(
                prefix="lecturepilot-source-", suffix=".zip"
            ) as body:
                if not self._read_body(body, length):
                    return
                body.flush()
                try:
                    pdf = self.server.compile_function(Path(body.name), main_paths[0])
                except CompilerServiceError as exc:
                    self._json_error(exc.status, exc.code, exc.message)
                    return
                except Exception as exc:
                    self.request_diagnostics.record_exception(exc)
                    self._json_error(
                        500,
                        "internal_error",
                        "LaTeX slide rendering failed safely.",
                    )
                    return
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(pdf)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Request-ID", self.request_diagnostics.request_id)
            self.request_diagnostics.record(200, "ok")
            self.end_headers()
            self.wfile.write(pdf)
        finally:
            self.server.compile_slot.release()

    def _content_length(self) -> int | None:
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            length = 0
        if length <= 0:
            self._json_error(411, "invalid_request", INVALID_REQUEST)
            return None
        if length > MAX_ARCHIVE_BYTES:
            self.close_connection = True
            self._json_error(
                413, "archive_limit", "The source archive exceeds compilation limits."
            )
            return None
        return length

    def _read_body(self, output, length: int) -> bool:
        remaining = length
        while remaining:
            chunk = self.rfile.read(min(1024 * 1024, remaining))
            if not chunk:
                self._json_error(400, "invalid_request", INVALID_REQUEST)
                return False
            output.write(chunk)
            remaining -= len(chunk)
        return True

    def _json_error(self, status: int, code: str, message: str) -> None:
        diagnostics = getattr(self, "request_diagnostics", None)
        if diagnostics is not None:
            diagnostics.record(status, code)
        self._write_json(status, {"error": {"code": code, "message": message}})

    def _write_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        diagnostics = getattr(self, "request_diagnostics", None)
        if diagnostics is not None:
            self.send_header("X-Request-ID", diagnostics.request_id)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def create_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    *,
    compile_function: CompileFunction = compile_archive,
) -> CompilerHTTPServer:
    return CompilerHTTPServer((host, port), compile_function)


def main() -> None:
    configure_logging()
    create_server().serve_forever()


if __name__ == "__main__":
    main()
