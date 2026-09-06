import json

from lecturepilot.canvas_markdown import CanvasMarkdownError, parse_section_frontmatter
from lecturepilot.canvas_signatures import is_student_section
from lecturepilot.models import CanvasCommand
from lecturepilot.learner_canvas_markdown import read_student_sections


def contextual_placement(executor, resolved, content, section_id):
    if section_id is None:
        return content
    fields = parse_section_frontmatter(content)
    mode, anchor = fields.get("placement_mode"), fields.get("placement_section_id")
    if mode is None and anchor is None:
        if resolved.path.exists():
            previous = parse_section_frontmatter(executor.workspace_fs.read_text(resolved.logical))
            mode, anchor = previous.get("placement_mode"), previous.get("placement_section_id")
        else:
            anchor = executor.focus_section_id or executor.initial_focus_section_id
            mode = "after_section" if anchor else None
        if mode is None and anchor is None:
            return content
        end = content.find("\n---", 4)
        content = (
            content[:end]
            + f"\nplacement_mode: {json.dumps(mode)}"
            + f"\nplacement_section_id: {json.dumps(anchor)}"
            + content[end:]
        )
    workspace = executor.canvas_workspace
    snapshot = workspace.course_canvas_store.read_current_published_snapshot(
        course_id=executor.course_id, lecture_id=executor.lecture_id
    )
    students = read_student_sections(
        workspace.layout.user_canvas_dir(executor.user_id, executor.course_id, executor.lecture_id),
        course_id=executor.course_id,
        lecture_id=executor.lecture_id,
    )
    valid_ids = {section.id for section in students}
    if snapshot:
        valid_ids.update(section.id for section in snapshot.document.sections)
    if (
        mode not in {"after_section", "before_section"}
        or anchor == section_id
        or anchor not in valid_ids
    ):
        raise CanvasMarkdownError("Placement must reference a different existing canvas section.")
    return content


def learner_update_commands(executor):
    document = executor.canvas_workspace.read_document(
        course_id=executor.course_id, lecture_id=executor.lecture_id, user_id=executor.user_id
    )
    # Use the compiled order so multiple notes at the same anchor keep their order live too.
    return [
        CanvasCommand(
            type="update_section",
            section_id=section.id,
            section=section,
            placement=(
                {"mode": "after_section", "section_id": document.sections[index - 1].id}
                if index
                else {"mode": "before_section", "section_id": first_official.id}
                if (
                    first_official := next(
                        (item for item in document.sections if not is_student_section(item)), None
                    )
                )
                else None
            ),
        )
        for index, section in enumerate(document.sections)
        if is_student_section(section)
    ]
