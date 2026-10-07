"""Interleave lecture queues while retaining oldest-due order within each lecture."""

from collections import deque
from datetime import datetime


def interleave_lectures(items):
    if items and all(hasattr(item, "due_at") for item in items):
        # Interleave ties only; an earlier due date always has priority.
        by_due = {}
        for item in sorted(items, key=lambda item: datetime.fromisoformat(item.due_at)):
            by_due.setdefault(datetime.fromisoformat(item.due_at), []).append(item)
        return [item for group in by_due.values() for item in _interleave(group)]
    return _interleave(items)


def _interleave(items):
    groups = {}
    for item in items:
        groups.setdefault(item.lecture_id, deque()).append(item)
    result = []
    active = deque(groups.values())
    while active:
        group = active.popleft()
        result.append(group.popleft())
        if group:
            active.append(group)
    return result
