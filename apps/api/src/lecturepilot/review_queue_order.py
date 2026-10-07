"""Interleave lecture queues while retaining oldest-due order within each lecture."""

from collections import deque


def interleave_lectures(items):
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
