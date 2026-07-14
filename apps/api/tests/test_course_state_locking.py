import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from threading import Event

from fastapi.testclient import TestClient
import pytest

from auth_helpers import professor_headers
import lecturepilot.course_builder_source as builder_source
import lecturepilot.course_routes as course_routes
import lecturepilot.course_update_routes as course_update_routes
import lecturepilot.lecture_access_routes as access_routes
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.course_update_storage import course_update_lock
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture
from lecturepilot.source_bundle_canvas import SourceBundleCanvasError


def test_visibility_read_modify_write_uses_course_lock(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path)
    _seed(client, "visibility-lock")
    entered = Event()
    original = access_routes.read_course_workspace

    def observed_read(*args, **kwargs):
        entered.set()
        return original(*args, **kwargs)

    monkeypatch.setattr(access_routes, "read_course_workspace", observed_read)
    root = client.app.state.canvas_workspace.layout.course_root("visibility-lock")
    response = _after_lock_release(
        root,
        entered,
        lambda: client.put(
            "/admin/courses/visibility-lock/lectures/lecture-01/access",
            headers=professor_headers(),
            json={
                "rule": {
                    "audience": "instructors_only",
                    "publication_mode": "hidden",
                },
                "confirm_university_members": False,
            },
        ),
    )
    assert response.status_code == 200


def test_workspace_create_and_live_upload_use_course_lock(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path)
    create_entered = Event()
    original_write = course_routes.write_course_workspace

    def observed_write(*args, **kwargs):
        create_entered.set()
        return original_write(*args, **kwargs)

    monkeypatch.setattr(course_routes, "write_course_workspace", observed_write)
    create_root = client.app.state.canvas_workspace.layout.course_root("lock-create")
    response = _after_lock_release(
        create_root,
        create_entered,
        lambda: client.post(
            "/admin/course-workspaces",
            headers=professor_headers(),
            json={
                "course_title": "Lock Create",
                "lecture_number": "01",
                "lecture_title": "First",
            },
        ),
    )
    assert response.status_code == 200

    upload_entered = Event()
    original_upload = course_routes.promote_course_upload

    def observed_upload(*args, **kwargs):
        upload_entered.set()
        return original_upload(*args, **kwargs)

    monkeypatch.setattr(course_routes, "promote_course_upload", observed_upload)
    response = _after_lock_release(
        create_root,
        upload_entered,
        lambda: client.post(
            "/admin/courses/lock-create/materials",
            headers=professor_headers(),
            data={"path": "Lecture01.tex"},
            files={"file": ("Lecture01.tex", b"\\documentclass{beamer}", "text/plain")},
        ),
    )
    assert response.status_code == 200


def test_async_routes_do_not_suspend_inside_course_lock() -> None:
    violations = []
    for module in (course_routes, course_update_routes):
        source_path = Path(module.__file__)
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.With) or not _locks_course_state(node):
                continue
            if any(isinstance(child, ast.Await) for child in ast.walk(node)):
                violations.append(f"{source_path.name}:{node.lineno}")
    assert violations == []


def test_manifest_generation_uses_course_lock(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path)
    _seed(client, "generation-lock")
    entered = Event()
    original = builder_source.refresh_course_source_index

    def observed_refresh(*args, **kwargs):
        entered.set()
        return original(*args, **kwargs)

    monkeypatch.setattr(builder_source, "refresh_course_source_index", observed_refresh)
    root = client.app.state.canvas_workspace.layout.course_root("generation-lock")
    with pytest.raises(SourceBundleCanvasError):
        _after_lock_release(
            root,
            entered,
            lambda: builder_source.course_builder_source_document(
                client.app, "generation-lock", "lecture-01"
            ),
        )


def _after_lock_release(root: Path, entered: Event, action):
    with ThreadPoolExecutor(max_workers=1) as executor:
        with course_update_lock(root):
            future = executor.submit(action)
            assert not entered.wait(timeout=0.1)
        assert entered.wait(timeout=2)
        return future.result(timeout=2)


def _locks_course_state(node: ast.With) -> bool:
    return any(
        isinstance(item.context_expr, ast.Call)
        and isinstance(item.context_expr.func, ast.Name)
        and item.context_expr.func.id == "locked_course_state"
        for item in node.items
    )


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    return TestClient(app)


def _seed(client: TestClient, course_id: str) -> None:
    workspace = CourseWorkspaceResult(
        course=Course(
            id=course_id,
            title="Lock Test",
            professor="Professor",
            term="Sommer 2026",
        ),
        lectures=[
            Lecture(
                id="lecture-01",
                course_id=course_id,
                title="First",
                date=date(2026, 5, 6),
            )
        ],
        active_lecture_id="lecture-01",
    )
    write_course_workspace(
        client.app.state.canvas_workspace.layout.course_root(course_id), workspace
    )
