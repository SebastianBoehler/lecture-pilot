from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_ai import ModelRetry

from lecturepilot.authoring_models import (
    AuthoringMetrics,
    AuthoringStalledError,
)
from lecturepilot.authoring_quality import AuthoringQualityMemo
from lecturepilot.authoring_workspace import AUTHORING_INPUT_ERRORS, AuthoringWorkspace
from lecturepilot.agent_tool_utils import AgentToolArgumentError
from lecturepilot.course_canvas_practice_support import source_for_practice_review
from lecturepilot.workspace_fs import WorkspaceFSError

if TYPE_CHECKING:
    from lecturepilot.authoring_job import AuthoringJob


class AuthoringTools:
    def __init__(self, job: AuthoringJob, workspace: AuthoringWorkspace, metrics: AuthoringMetrics):
        self.job, self.workspace, self.metrics = job, workspace, metrics
        self.accepted_digest: str | None = None
        self.failures: dict[str, int] = {}
        self.quality = AuthoringQualityMemo()

    def ls(self, path: str = "/") -> list[str]:
        """List available evidence and draft file paths."""
        self.job.authorize()
        self.metrics.tool_calls += 1
        if path == "/":
            return self.workspace.fs.logical_roots()
        try:
            return [p.logical for p in self.workspace.fs.files(path)]
        except (WorkspaceFSError, AgentToolArgumentError) as exc:
            raise ModelRetry(str(exc)) from exc

    def read(self, path: str, offset: int = 0) -> dict:
        """Read up to 16000 characters; use next_offset to continue without truncation."""
        self.job.authorize()
        self.metrics.tool_calls += 1
        try:
            text = self.workspace.fs.read_text(path)
            if offset < 0 or offset > len(text):
                raise WorkspaceFSError("Offset is outside the file.")
            end = offset + 16_000
            return {"text": text[offset:end], "next_offset": end if end < len(text) else None}
        except (WorkspaceFSError, AgentToolArgumentError, OSError) as exc:
            raise ModelRetry("Cannot read the requested workspace file: " + str(exc)) from exc

    def search(self, text: str, path: str = "/evidence") -> list[dict]:
        """Find literal text within authorized files; returns at most twenty excerpts."""
        matches = []
        for file_path in self.ls(path):
            content = self.workspace.fs.read_text(file_path)
            offset = content.casefold().find(text.casefold())
            if offset >= 0:
                matches.append(
                    {
                        "path": file_path,
                        "offset": offset,
                        "excerpt": content[max(0, offset - 100) : offset + 500],
                    }
                )
            if len(matches) == 20:
                break
        return matches

    def write(self, path: str, text: str) -> dict:
        """Write an assigned draft section as Markdown. Source files are read-only."""
        self.metrics.tool_calls += 1
        try:
            self.workspace.write(path, text)
            return {"written": path}
        except WorkspaceFSError as exc:
            raise ModelRetry(str(exc)) from exc

    def edit(self, path: str, old: str, new: str) -> dict:
        """Replace one exact, unique string in a draft. Read again on conflict."""
        self.job.authorize()
        try:
            content = self.workspace.fs.read_text(path)
            if not old or content.count(old) != 1:
                raise WorkspaceFSError("Edit requires exactly one match; read the current file.")
            result = self.write(path, content.replace(old, new, 1))
            self.metrics.repair_edits += 1
            return result
        except (WorkspaceFSError, AgentToolArgumentError, OSError) as exc:
            raise ModelRetry(str(exc)) from exc

    async def validate(self) -> dict:
        """Check all draft sections, exact approved tasks, math, and source-grounded teaching."""
        self.job.authorize()
        self.metrics.tool_calls += 1
        digest = self.workspace.digest()
        try:
            document = self.workspace.document()
        except AUTHORING_INPUT_ERRORS as exc:
            return self._invalid(digest, [str(exc)])
        if self.accepted_digest != digest:
            self.metrics.quality_reviews += 1
            issues = await self.quality.review(
                self.job.reviewer,
                settings=self.job.settings,
                source_document=source_for_practice_review(
                    self.job.source, document, self.job.design
                ),
                candidate_document=document,
            )
            if issues:
                protected = {"practice-" + target.id for target in self.job.design.targets}
                verified = []
                for issue in issues:
                    if issue.block_id in protected:
                        issue = await self.job.checkpoint_reviewer.resolve(
                            job=self.job, document=document, issue=issue
                        )
                    if issue is not None:
                        verified.append(issue.model_dump(mode="json"))
                if verified:
                    return self._invalid(digest, verified)
            self.accepted_digest = digest
        return {"valid": True, "issues": [], "draft_digest": digest}

    def _invalid(self, digest: str, issues: list) -> dict:
        self.metrics.validation_failures += 1
        key = repr((digest, issues))
        self.failures[key] = self.failures.get(key, 0) + 1
        if self.failures[key] >= 3:
            raise AuthoringStalledError(
                "Authoring repeated the same invalid draft defect three times."
            )
        return {"valid": False, "issues": issues}
