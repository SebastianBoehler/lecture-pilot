from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from lecturepilot.agent_canvas_write import prepare_student_canvas_write
from lecturepilot.agent_highlight import highlight_command_for
from lecturepilot.agent_image_tool import AgentImageToolError, generate_workspace_image
from lecturepilot.agent_tool_utils import (
    AgentToolArgumentError,
    ToolPath,
    file_entry,
    int_arg,
    is_text_file,
    normalize_logical_path,
    relative_write_path,
    required_str,
)
from lecturepilot.canvas_markdown import CanvasMarkdownError, read_document_source
from lecturepilot.canvas_signatures import is_student_section
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.models import CanvasCommand, QualityGateDecision
from lecturepilot.storage_layout import safe_id
from lecturepilot.workspace import WorkspacePolicy, WorkspacePolicyError

_WRITE_PREFIXES = (
    "/lecture/canvas/student/", "/lecture/canvas/components/", "/lecture/canvas/student-assets/", "/user/memories/",
)
class AgentToolError(RuntimeError):
    pass
class AgentToolExecutor:
    def __init__(
        self,
        *,
        canvas_workspace: CanvasWorkspace,
        course_id: str,
        lecture_id: str,
        user_id: str,
        image_generator: Any | None = None,
    ) -> None:
        self.canvas_workspace = canvas_workspace
        self.course_id = course_id
        self.lecture_id = lecture_id
        self.user_id = user_id
        self.image_generator = image_generator
        self.policy = WorkspacePolicy()
        self.focus_section_id: str | None = None
        self.highlight_command: CanvasCommand | None = None
        self.gate: QualityGateDecision | None = None
        self.canvas_changed = False
        self.latest_written_section_id: str | None = None

    def execute(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        try:
            return {"ok": True, **self._execute(name, args)}
        except (
            AgentToolError,
            WorkspacePolicyError,
            CanvasMarkdownError,
            AgentImageToolError,
            AgentToolArgumentError,
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
            return self._highlight(required_str(args, "span_id"), required_str(args, "highlight_text", ""))
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
        base = resolved.path if resolved.path.is_dir() else resolved.path.parent
        matches = []
        for item in sorted(base.glob(glob)):
            if item.name.startswith(".") or not item.exists():
                continue
            matches.append(file_entry(self._logical_for(item), item))
            if len(matches) >= max_results:
                break
        return {"matches": matches}

    def _grep(self, pattern: str, logical_path: str, max_matches: int) -> dict[str, Any]:
        regex = re.compile(pattern, re.IGNORECASE)
        resolved = self._resolve(logical_path)
        files = [resolved.path] if resolved.path.is_file() else sorted(resolved.path.rglob("*"))
        matches = []
        for path in files:
            if not is_text_file(path):
                continue
            for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if regex.search(line):
                    matches.append(
                        {
                            "path": self._logical_for(path),
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
        text = resolved.path.read_text(encoding="utf-8", errors="ignore")
        return {"path": resolved.logical, "content": text[:max_chars], "truncated": len(text) > max_chars}

    def _write(self, logical_path: str, content: str) -> dict[str, Any]:
        resolved = self._resolve(logical_path, for_write=True)
        path, content, section_id = prepare_student_canvas_write(resolved.logical, resolved.path, content)
        if path != resolved.path:
            resolved = ToolPath(self._logical_for(path), path)
        self.policy.validate_write(relative_write_path(resolved.logical), len(content.encode("utf-8")))
        previous = resolved.path.read_text(encoding="utf-8") if resolved.path.exists() else None
        resolved.path.parent.mkdir(parents=True, exist_ok=True)
        resolved.path.write_text(content, encoding="utf-8")
        self._validate_canvas_write(resolved, previous)
        self.latest_written_section_id = section_id or self.latest_written_section_id
        return {"path": resolved.logical, "bytes": len(content.encode("utf-8")), "section_id": section_id}

    def _edit(self, logical_path: str, old_text: str, new_text: str) -> dict[str, Any]:
        resolved = self._resolve(logical_path, for_write=True)
        if not resolved.path.exists():
            raise AgentToolError("File does not exist.")
        current = resolved.path.read_text(encoding="utf-8")
        if old_text not in current:
            raise AgentToolError("old_text was not found exactly once.")
        updated = current.replace(old_text, new_text, 1)
        self.policy.validate_write(relative_write_path(resolved.logical), len(updated.encode("utf-8")))
        resolved.path.write_text(updated, encoding="utf-8")
        self._validate_canvas_write(resolved, current)
        return {"path": resolved.logical, "replacements": 1}

    def _highlight(self, span_id: str, highlight_text: str) -> dict[str, Any]:
        self.highlight_command = highlight_command_for(
            canvas_workspace=self.canvas_workspace, user_id=self.user_id, course_id=self.course_id,
            lecture_id=self.lecture_id, focus_section_id=self.focus_section_id, span_id=span_id,
            highlight_text=highlight_text,
        )
        return {"span_id": self.highlight_command.span_id, "highlight_text": self.highlight_command.highlight_text}

    def _remember(self, args: dict[str, Any]) -> dict[str, Any]:
        memories = self.canvas_workspace.layout.user_memories_dir(self.user_id)
        memories.mkdir(parents=True, exist_ok=True)
        note = required_str(args, "note").strip()
        if note:
            global_path = memories / "global.md"
            current = global_path.read_text(encoding="utf-8") if global_path.exists() else ""
            global_path.write_text((current.rstrip() + f"\n- {note}\n").lstrip(), encoding="utf-8")
        key = str(args.get("preference_key") or "").strip()
        if key:
            pref_path = memories / "preferences.json"
            prefs = json.loads(pref_path.read_text(encoding="utf-8") or "{}") if pref_path.exists() else {}
            prefs[key] = str(args.get("preference_value") or "")
            pref_path.write_text(json.dumps(prefs, indent=2), encoding="utf-8")
        return {"memory": "updated"}

    def _generate_image(self, args: dict[str, Any]) -> dict[str, Any]:
        return generate_workspace_image(
            image_generator=self.image_generator,
            layout=self.canvas_workspace.layout,
            user_id=self.user_id,
            course_id=self.course_id,
            lecture_id=self.lecture_id,
            prompt=required_str(args, "prompt"),
            section_id=required_str(args, "section_id", "student-generated-image"),
            filename=str(args.get("filename") or "") or None,
        )

    def _validate_canvas_write(self, resolved: ToolPath, previous: str | None) -> None:
        if not resolved.logical.startswith("/lecture/canvas/"):
            return
        try:
            read_document_source(self.canvas_workspace.layout.user_canvas_dir(self.user_id, self.course_id, self.lecture_id))
        except Exception:
            if previous is None:
                resolved.path.unlink(missing_ok=True)
            else:
                resolved.path.write_text(previous, encoding="utf-8")
            raise
        self.canvas_changed = True

    def _resolve(self, logical_path: str, *, for_write: bool = False) -> ToolPath:
        normalized = normalize_logical_path(logical_path)
        if for_write and not any(normalized.startswith(prefix) for prefix in _WRITE_PREFIXES):
            raise AgentToolError("This path is read-only for the tutor agent.")
        for prefix, root in self._root_map().items():
            if normalized == prefix or normalized.startswith(f"{prefix}/"):
                relative = normalized.removeprefix(prefix).lstrip("/")
                target = (root / relative).resolve()
                try:
                    target.relative_to(root.resolve())
                except ValueError as exc:
                    raise AgentToolError("Resolved path escapes the workspace root.") from exc
                return ToolPath(normalized, target)
        raise AgentToolError(f"Path is outside the agent workspace: {logical_path}")

    def _root_map(self) -> dict[str, Path]:
        layout = self.canvas_workspace.layout
        return {
            "/lecture/canvas": layout.user_canvas_dir(self.user_id, self.course_id, self.lecture_id),
            "/user/memories": layout.user_memories_dir(self.user_id),
            "/user/profile.json": layout.user_root(self.user_id) / "profile.json",
            "/course/canvas": layout.course_canvas_dir(self.course_id, self.lecture_id),
            "/course/source/uploads": layout.course_uploads_dir(self.course_id),
            "/course/materials": self.canvas_workspace.material_root,
        }

    def _roots(self) -> list[str]:
        return sorted(self._root_map())

    def _logical_for(self, path: Path) -> str:
        resolved = path.resolve()
        for prefix, root in sorted(self._root_map().items(), key=lambda item: len(str(item[1])), reverse=True):
            try:
                return f"{prefix}/{resolved.relative_to(root.resolve())}".rstrip("/")
            except ValueError:
                continue
        return "/"
