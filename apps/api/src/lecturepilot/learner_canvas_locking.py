from __future__ import annotations

from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from lecturepilot.canvas_snapshot import locked_canvas_paths


_P = ParamSpec("_P")
_R = TypeVar("_R")


def serialized_canvas_write(method: Callable[_P, _R]) -> Callable[_P, _R]:
    @wraps(method)
    def wrapped(self, logical_path: str, *args, **kwargs):
        if not logical_path.startswith("/lecture/canvas/"):
            return method(self, logical_path, *args, **kwargs)
        self.canvas_workspace.read_document(
            course_id=self.course_id,
            lecture_id=self.lecture_id,
            user_id=self.user_id,
        )
        canvas_dir = self.canvas_workspace.layout.user_canvas_dir(
            self.user_id,
            self.course_id,
            self.lecture_id,
        )
        with locked_canvas_paths(canvas_dir):
            canvas_dir.mkdir(parents=True, exist_ok=True)
            return method(self, logical_path, *args, **kwargs)

    return wrapped
