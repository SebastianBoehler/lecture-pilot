from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Lock

import pytest

from canvas_workspace_fixtures import published_course_canvas
from lecturepilot import course_canvas_store as course_canvas_store_module
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_store import CourseCanvasStore
from lecturepilot.storage_layout import StorageLayout


def test_failed_draft_write_preserves_existing_draft(tmp_path: Path, monkeypatch) -> None:
    store = _store(tmp_path)
    existing = published_course_canvas("demo-course", "lecture-01")
    store.write_draft(existing)
    _inject_partial_write_failure(monkeypatch, "injected draft write failure")

    with pytest.raises(OSError, match="injected draft write failure"):
        store.write_draft(existing.model_copy(update={"title": "Replacement"}))

    preserved = store.read_draft(course_id="demo-course", lecture_id="lecture-01")
    assert preserved is not None
    assert preserved.title == existing.title


def test_failed_live_canvas_write_preserves_existing_canvas(tmp_path: Path, monkeypatch) -> None:
    store = _store(tmp_path)
    existing = published_course_canvas("demo-course", "lecture-01")
    store.write(existing)
    _inject_partial_write_failure(monkeypatch, "injected live canvas write failure")

    with pytest.raises(OSError, match="injected live canvas write failure"):
        store.write(existing.model_copy(update={"title": "Replacement"}))

    preserved = store.read(
        course_id="demo-course",
        lecture_id="lecture-01",
        workspace_path="canvas/index.md",
    )
    assert preserved is not None
    assert preserved.title == existing.title


def test_failed_publish_preserves_document_and_version(tmp_path: Path, monkeypatch) -> None:
    store = _store(tmp_path)
    original = published_course_canvas("demo-course", "lecture-01")
    store.write_draft(original)
    assert _publish(store, "professor")["version"] == 1
    store.write_draft(original.model_copy(update={"title": "Replacement"}))

    def fail_learning_map(*_args, **_kwargs) -> None:
        raise OSError("injected publication write failure")

    monkeypatch.setattr(course_canvas_store_module, "write_learning_map", fail_learning_map)

    with pytest.raises(OSError, match="injected publication write failure"):
        _publish(store, "professor")

    published = store.read(
        course_id="demo-course",
        lecture_id="lecture-01",
        workspace_path="canvas/index.md",
    )
    metadata = store.publication(course_id="demo-course", lecture_id="lecture-01")
    assert published is not None
    assert published.title == original.title
    assert metadata is not None
    assert metadata["version"] == 1


def test_concurrent_publishes_are_serialized_and_increment_versions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path)
    store.write_draft(published_course_canvas("demo-course", "lecture-01"))
    assert _publish(store, "professor")["version"] == 1
    original_write = course_canvas_store_module.write_document_source
    first_entered = Event()
    second_entered = Event()
    release_first = Event()
    call_lock = Lock()
    call_count = 0

    def controlled_write(document: CanvasDocument, canvas_dir: Path) -> None:
        nonlocal call_count
        with call_lock:
            call_count += 1
            call_number = call_count
        if call_number == 1:
            first_entered.set()
            assert release_first.wait(timeout=2)
        elif call_number == 2:
            second_entered.set()
        original_write(document, canvas_dir)

    monkeypatch.setattr(course_canvas_store_module, "write_document_source", controlled_write)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(_publish, store, "professor-a")
        assert first_entered.wait(timeout=2)
        second = executor.submit(_publish, store, "professor-b")
        assert not second_entered.wait(timeout=0.2)
        release_first.set()
        versions = sorted([first.result(timeout=2)["version"], second.result(timeout=2)["version"]])

    assert versions == [2, 3]
    metadata = store.publication(course_id="demo-course", lecture_id="lecture-01")
    assert metadata is not None
    assert metadata["version"] == 3


def _store(tmp_path: Path) -> CourseCanvasStore:
    return CourseCanvasStore(StorageLayout(tmp_path / "workspaces"))


def _publish(store: CourseCanvasStore, published_by: str) -> dict:
    return store.publish_draft(
        course_id="demo-course",
        lecture_id="lecture-01",
        published_by=published_by,
    )


def _inject_partial_write_failure(monkeypatch, message: str) -> None:
    original_write = course_canvas_store_module.write_document_source

    def fail_after_partial_write(document: CanvasDocument, canvas_dir: Path) -> None:
        original_write(document, canvas_dir)
        raise OSError(message)

    monkeypatch.setattr(
        course_canvas_store_module, "write_document_source", fail_after_partial_write
    )
