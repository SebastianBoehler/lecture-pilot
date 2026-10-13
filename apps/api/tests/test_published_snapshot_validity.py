from __future__ import annotations

import os
from pathlib import Path

import pytest

from lecturepilot.canvas.published_snapshot_validity import PublishedSnapshotValidity


def _published(tmp_path: Path) -> Path:
    published = tmp_path / "lecture-01"
    (published / "sections").mkdir(parents=True)
    (published / "index.md").write_text("index", encoding="utf-8")
    (published / "publication.json").write_text("{}", encoding="utf-8")
    (published / "sections" / "01.md").write_text("one", encoding="utf-8")
    return published


class Validator:
    def __init__(self, result: bool | Exception = True) -> None:
        self.result = result
        self.calls = 0

    def __call__(self) -> bool:
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_unchanged_snapshot_is_validated_once(tmp_path: Path) -> None:
    published = _published(tmp_path)
    cache, validate = PublishedSnapshotValidity(), Validator()

    assert cache.check(published, validate) is True
    assert cache.check(published, validate) is True
    assert validate.calls == 1


def test_any_changed_file_is_validated_again(tmp_path: Path) -> None:
    published = _published(tmp_path)
    cache, validate = PublishedSnapshotValidity(), Validator()
    cache.check(published, validate)

    section = published / "sections" / "01.md"
    section.write_text("one, edited", encoding="utf-8")
    stat = section.stat()
    os.utime(section, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    cache.check(published, validate)
    (published / "sections" / "02.md").write_text("two", encoding="utf-8")
    cache.check(published, validate)

    assert validate.calls == 3


def test_replaced_snapshot_directory_is_validated_again(tmp_path: Path) -> None:
    published = _published(tmp_path)
    cache, validate = PublishedSnapshotValidity(), Validator()
    cache.check(published, validate)

    published.rename(tmp_path / "old")
    _published(tmp_path)
    cache.check(published, validate)

    assert validate.calls == 2


def test_invalid_snapshot_error_is_remembered_and_raised_again(tmp_path: Path) -> None:
    published = _published(tmp_path)
    cache, validate = PublishedSnapshotValidity(), Validator(ValueError("invalid snapshot"))

    for _ in range(2):
        with pytest.raises(ValueError, match="invalid snapshot"):
            cache.check(published, validate)
    assert validate.calls == 1


def test_missing_snapshot_is_never_cached(tmp_path: Path) -> None:
    cache, validate = PublishedSnapshotValidity(), Validator(False)

    assert cache.check(tmp_path / "missing", validate) is False
    assert cache.check(tmp_path / "missing", validate) is False
    assert validate.calls == 2
