"""Bounded regular-expression searches over capability-scoped files."""

from time import monotonic

import regex

from lecturepilot.agent_tool_utils import AgentToolArgumentError, is_text_file
from lecturepilot.workspace_fs import WorkspaceFS


def search_workspace(fs: WorkspaceFS, path: str, pattern: str, max_matches: int) -> dict:
    try:
        expression = regex.compile(pattern, regex.IGNORECASE)
    except regex.error as exc:
        raise AgentToolArgumentError("Invalid search regular expression.") from exc
    deadline = monotonic() + 0.1
    matches = []
    for item in fs.files(path):
        if not is_text_file(item.path):
            continue
        text = fs.read_text(item.logical, errors="ignore")
        for line_number, line in enumerate(text.splitlines(), 1):
            try:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise TimeoutError
                found = expression.search(line, timeout=remaining, concurrent=True)
            except TimeoutError as exc:
                raise AgentToolArgumentError(
                    "Search regular expression exceeded its time limit."
                ) from exc
            if found:
                matches.append(
                    {"path": item.logical, "line": line_number, "text": line.strip()[:500]}
                )
                if len(matches) >= max_matches:
                    return {"matches": matches}
    return {"matches": matches}
