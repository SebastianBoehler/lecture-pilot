from lecturepilot.canvas_models import MAX_SOURCE_REF_LENGTH


_PLANNER_SOURCE_PREFIX = "course planner from "


def planned_source_ref(source_ref: str) -> str:
    """Identify generated content without dropping already-bounded source evidence."""
    prefixed = f"{_PLANNER_SOURCE_PREFIX}{source_ref}"
    if len(prefixed) <= MAX_SOURCE_REF_LENGTH:
        return prefixed
    return source_ref[:MAX_SOURCE_REF_LENGTH]
