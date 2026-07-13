from __future__ import annotations

import re
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from lecturepilot.agent_canvas_write import prepare_student_canvas_write
from lecturepilot.agent_image_placement import AgentImagePlacement, dedupe_markdown_image_refs
from lecturepilot.agent_image_tool import AgentImageToolError
from lecturepilot.agent_side_effect_tools import AgentSideEffectError, AgentSideEffectTools
from lecturepilot.agent_tool_utils import (
    AgentToolArgumentError,
    ToolPath,
    file_entry,
    int_arg,
    is_text_file,
    relative_write_path,
    required_str,
)
from lecturepilot.canvas_markdown import CanvasMarkdownError, read_document_source
from lecturepilot.canvas_signatures import is_student_section
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.models import CanvasCommand, QualityGateDecision
from lecturepilot.storage_layout import safe_id
from lecturepilot.usage_quota import UsageQuota, UsageQuotaExceeded
from lecturepilot.workspace import WorkspacePolicy, WorkspacePolicyError
from lecturepilot.workspace_capability import learner_workspace_capability
from lecturepilot.workspace_fs import WorkspaceFS, WorkspaceFSError


class AgentToolError(RuntimeError):
    pass


class AgentToolExecutor(AgentSideEffectTools):
    def __init__(
        self,
        *,
        canvas_workspace: CanvasWorkspace,
        course_id: str,
        lecture_id: str,
        user_id: str,
        quota_user_id: str | None = None,
        image_generator: Any | None = None,
        usage_quota: UsageQuota | None = None,
        tenant_id: str | None = None,
        user_message: str | None = None,
    ) -> None:
        self.canvas_workspace = canvas_workspace
        self.course_id = course_id
        self.lecture_id = lecture_id
        self.user_id = user_id
        self.quota_user_id = quota_user_id or user_id
        self.image_generator = image_generator
        self.usage_quota = usage_quota
        self.tenant_id = tenant_id
        self.user_message = user_message
        self.workspace_fs = WorkspaceFS(
            learner_workspace_capability(
                canvas_workspace,
                user_id=user_id,
                course_id=course_id,
                lecture_id=lecture_id,
            )
        )
        self.policy = WorkspacePolicy()
        self.focus_section_id: str | None = None
        self.highlight_command: CanvasCommand | None = None
        self.gate: QualityGateDecision | None = None
        self.canvas_changed = False
        self.latest_written_section_id: str | None = None
        self.image_placement: AgentImagePlacement | None = None

    def execute(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        try:
            return {"ok": True, **self._execute(name, args)}
        except (
            AgentToolError,
            WorkspacePolicyError,
            CanvasMarkdownError,
            AgentImageToolError,
            AgentToolArgumentError,
            WorkspaceFSError,
            UsageQuotaExceeded,
            AgentSideEffectError,
        ) as exc:
            return {"ok": False, "error": str(exc)}

    def canvas_update_commands(self) -> list[CanvasCommand]:
        commands: list[CanvasCommand] = []
        if self.canvas_changed:
            document = self.canvas_workspace.read_document(
                course_id=self.course_id,
                lecture_id=self.lecture_id,
                user_id=self.user_id,
            )
            commands.extend(
                CanvasCommand(type="update_section", section_id=section.id, section=section)
                for section in document.sections
                if is_student_section(section)
            )
        focus_id = self.focus_section_id or self.latest_written_section_id
        if focus_id:
            commands.append(CanvasCommand(type="focus_section", section_id=focus_id))
        if self.highlight_command:
            commands.append(self.highlight_command)
        return commands

    def _execute(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "pwd":
            return {"roots": self._roots()}
        if name == "ls":
            return self._ls(required_str(args, "path", "/"))
        if name == "find":
            return self._find(
                required_str(args, "path", "/"),
                required_str(args, "glob", "**/*"),
                int_arg(args, "max_results", 40),
            )
        if name == "grep":
            return self._grep(
                required_str(args, "pattern"),
                required_str(args, "path", "/"),
                int_arg(args, "max_matches", 40),
            )
        if name == "read":
            return self._read(required_str(args, "path"), int_arg(args, "max_chars", 12000))
        if name == "write":
            return self._write(required_str(args, "path"), required_str(args, "content"))
        if name == "edit":
            return self._edit(
                required_str(args, "path"),
                required_str(args, "old_text"),
                required_str(args, "new_text"),
            )
        if name == "focus":
            self.focus_section_id = safe_id(required_str(args, "section_id"))
            return {"section_id": self.focus_section_id}
        if name == "highlight":
            return self._highlight(
                required_str(args, "span_id"), required_str(args, "highlight_text", "")
            )
        if name == "record_gate":
            self.gate = QualityGateDecision.model_validate(args)
            return {"gate_id": self.gate.gate_id, "status": self.gate.status.value}
        if name == "remember":
            return self._remember(args)
        if name == "generate_image":
            return self._generate_image(args)
        raise AgentToolError(f"Unknown tool: {name}")

    def _ls(self, logical_path: str) -> dict[str, Any]:
        if logical_path == "/":
            return {"entries": [{"path": root, "type": "dir"} for root in self._roots()]}
        resolved = self._resolve(logical_path)
        if not resolved.path.exists():
            return {"entries": []}
        if resolved.path.is_file():
            return {"entries": [file_entry(resolved.logical, resolved.path)]}
        return {
            "entries": [
                file_entry(f"{resolved.logical.rstrip('/')}/{item.name}", item)
                for item in sorted(resolved.path.iterdir(), key=lambda item: item.name)
                if not item.name.startswith(".")
            ][:80]
        }

    def _find(self, logical_path: str, glob: str, max_results: int) -> dict[str, Any]:
        resolved = self._resolve(logical_path)
        if not resolved.path.exists():
            return {"matches": []}
        matches = []
        base = resolved.logical.rstrip("/")
        for item in sorted(
            self.workspace_fs.files(resolved.logical), key=lambda item: item.logical
        ):
            relative = item.logical.removeprefix(base).lstrip("/")
            top_level_glob = glob.removeprefix("**/")
            if not any(
                fnmatch(value, pattern)
                for value in (relative, item.path.name)
                for pattern in (glob, top_level_glob)
            ):
                continue
            matches.append(file_entry(item.logical, item.path))
            if len(matches) >= max_results:
                break
        return {"matches": matches}

    def _grep(self, pattern: str, logical_path: str, max_matches: int) -> dict[str, Any]:
        regex = re.compile(pattern, re.IGNORECASE)
        resolved = self._resolve(logical_path)
        files = self.workspace_fs.files(resolved.logical)
        matches = []
        for item in files:
            if not is_text_file(item.path):
                continue
            text = self.workspace_fs.read_text(item.logical, errors="ignore")
            for line_number, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    matches.append(
                        {
                            "path": item.logical,
                            "line": line_number,
                            "text": line.strip()[:500],
                        }
                    )
                    if len(matches) >= max_matches:
                        return {"matches": matches}
        return {"matches": matches}

    def _read(self, logical_path: str, max_chars: int) -> dict[str, Any]:
        resolved = self._resolve(logical_path)
        if not resolved.path.exists() or not resolved.path.is_file():
            raise AgentToolError("File does not exist.")
        if not is_text_file(resolved.path):
            raise AgentToolError("Only text files can be read through this tool.")
        text = self.workspace_fs.read_text(resolved.logical, errors="ignore")
        return {
            "path": resolved.logical,
            "content": text[:max_chars],
            "truncated": len(text) > max_chars,
        }

    def _write(self, logical_path: str, content: str) -> dict[str, Any]:
        resolved = self._resolve(logical_path, for_write=True)
        path, content, section_id = prepare_student_canvas_write(
            resolved.logical, resolved.path, content
        )
        if path != resolved.path:
            resolved = ToolPath(self.workspace_fs.logical_for(path, allow_missing=True), path)
        error = self._pending_image_write_error(resolved.logical, content)
        if error:
            raise AgentToolError(error)
        content = dedupe_markdown_image_refs(content)
        self.policy.validate_write(
            relative_write_path(resolved.logical), len(content.encode("utf-8"))
        )
        previous = self.workspace_fs.read_text(resolved.logical) if resolved.path.exists() else None
        self.workspace_fs.write_text(resolved.logical, content)
        self._validate_canvas_write(resolved, previous)
        self._clear_pending_image_insert(content)
        self.latest_written_section_id = section_id or self.latest_written_section_id
        return {
            "path": resolved.logical,
            "bytes": len(content.encode("utf-8")),
            "section_id": section_id,
        }

    def _edit(self, logical_path: str, old_text: str, new_text: str) -> dict[str, Any]:
        resolved = self._resolve(logical_path, for_write=True)
        if not resolved.path.exists():
            raise AgentToolError("File does not exist.")
        current = self.workspace_fs.read_text(resolved.logical)
        if old_text not in current:
            raise AgentToolError("old_text was not found exactly once.")
        updated = current.replace(old_text, new_text, 1)
        updated = dedupe_markdown_image_refs(updated)
        self.policy.validate_write(
            relative_write_path(resolved.logical), len(updated.encode("utf-8"))
        )
        self.workspace_fs.write_text(resolved.logical, updated)
        self._validate_canvas_write(resolved, current)
        self._clear_pending_image_insert(updated)
        return {"path": resolved.logical, "replacements": 1}

    def _validate_canvas_write(self, resolved: ToolPath, previous: str | None) -> None:
        if not resolved.logical.startswith("/lecture/canvas/"):
            return
        try:
            read_document_source(
                self.canvas_workspace.layout.user_canvas_dir(
                    self.user_id, self.course_id, self.lecture_id
                )
            )
        except Exception:
            if previous is None:
                resolved.path.unlink(missing_ok=True)
            else:
                self.workspace_fs.write_text(resolved.logical, previous)
            raise
        self.canvas_changed = True

    def _resolve(self, logical_path: str, *, for_write: bool = False) -> ToolPath:
        try:
            return self.workspace_fs.resolve(logical_path, for_write=for_write)
        except ValueError as exc:
            raise AgentToolError(str(exc)) from exc

    def _roots(self) -> list[str]:
        return self.workspace_fs.logical_roots()

    def _logical_for(self, path: Path) -> str:
        return self.workspace_fs.logical_for(path)
