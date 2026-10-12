"""Async code must not take course locks or parse sources on the event loop.

The course lock is a blocking flock that source parsing (conversion, LaTeX, PDF and OCR) can
hold for minutes. Taking it, or parsing, inside an ``async def`` freezes every request.
Run such work with ``run_in_threadpool`` (or ``anyio.to_thread``) instead.
"""

import ast
from pathlib import Path

import lecturepilot

BLOCKING = {
    "locked_course_state",
    "course_update_lock",
    "exclusive_file_lock",
    "course_builder_source_document",
    "course_builder_source_revision",
    "refresh_course_source_index",
    "normalize_selected_documents",
    "import_source_bundle_canvas",
    "_source_context",
    "_source_revision",
}


def _direct_calls(function: ast.AsyncFunctionDef) -> set[str]:
    found: set[str] = set()

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue  # Nested callables are what gets handed to a worker thread.
            if isinstance(child, ast.Call):
                func = child.func
                name = getattr(func, "id", None) or getattr(func, "attr", None)
                if name in BLOCKING:
                    found.add(name)
            visit(child)

    visit(function)
    return found


def test_async_functions_keep_blocking_course_work_off_the_event_loop() -> None:
    offenders = []
    for path in sorted(Path(lecturepilot.__file__).parent.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.AsyncFunctionDef) and (calls := _direct_calls(node)):
                offenders.append(f"{path.name}:{node.lineno} {node.name} -> {sorted(calls)}")
    assert not offenders, "\n".join(offenders)


PARSING = {
    "source_document",
    "source_context",
    "_source_context",
    "course_builder_source_document",
    "import_source_bundle_canvas",
    "normalize_selected_documents",
    "compile_latex_deck",
}


def test_source_parsing_never_runs_while_the_course_lock_is_held() -> None:
    offenders = []
    for path in sorted(Path(lecturepilot.__file__).parent.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.With) or not any(
                isinstance(item.context_expr, ast.Call)
                and _name(item.context_expr.func) == "locked_course_state"
                for item in node.items
            ):
                continue
            for call in ast.walk(node):
                if isinstance(call, ast.Call) and _name(call.func) in PARSING:
                    offenders.append(f"{path.name}:{call.lineno} {_name(call.func)}")
    assert not offenders, "\n".join(offenders)


def _name(func: ast.AST) -> str | None:
    return getattr(func, "id", None) or getattr(func, "attr", None)
