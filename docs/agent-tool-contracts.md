# Agent Tool Contracts

LecturePilot treats the tutor as a teacher agent inside a constrained
filesystem image. The model does not receive host filesystem access. It receives
typed tools over logical roots, and the backend maps those roots to tenant- and
student-scoped storage.

## Profiles

| Profile          | Tools                                                                                                   |
| ---------------- | ------------------------------------------------------------------------------------------------------- |
| `tutor`          | `pwd`, `ls`, `read`, `write`, `edit`, `focus`, `highlight`, `record_gate`, `remember`, `generate_image` |
| `evidence`       | tutor tools plus `find`, `grep`                                                                         |
| `course_builder` | `pwd`, `ls`, `find`, `grep`, `read`, `write`, `edit`, `generate_image`                                  |

The course-builder profile intentionally has no learner-state tools such as
`record_gate`, `remember`, `focus`, or `highlight`.

## Logical Roots

| Root                     | Purpose                                              |
| ------------------------ | ---------------------------------------------------- |
| `/lecture/canvas`        | learner-owned lecture canvas overlay                 |
| `/course/canvas`         | professor-approved published canvas                  |
| `/course/source/uploads` | professor-uploaded source bundle                     |
| `/user/memories`         | cross-course learner memory and preferences          |
| `/user/course/memories`  | course-specific learner memory for the active course |
| `/user/profile.json`     | learner profile file                                 |

Tutor writes are allowed only below `/lecture/canvas/student/`,
`/lecture/canvas/components/`, `/lecture/canvas/student-assets/`, and
`/user/memories/` or `/user/course/memories/`. Source material and published
course canvases are read-only from tutor turns.

## Tool Semantics

| Tool             | Required input                 | Side effect                                                                                                                               |
| ---------------- | ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `pwd`            | none                           | Returns available logical roots.                                                                                                          |
| `ls`             | `path`                         | Lists visible files and directories. Hidden files are skipped.                                                                            |
| `find`           | `path`, `glob`                 | Returns matching file entries, capped by `max_results`.                                                                                   |
| `grep`           | `pattern`, `path`              | Searches text files and returns matching lines.                                                                                           |
| `read`           | `path`                         | Reads text files only, capped by `max_chars`.                                                                                             |
| `write`          | `path`, `content`              | Creates or overwrites a permitted learner file. Canvas Markdown is validated and appended in render order.                                |
| `edit`           | `path`, `old_text`, `new_text` | Replaces one exact text occurrence in a permitted learner file.                                                                           |
| `focus`          | `section_id`                   | Queues a canvas focus command for the frontend.                                                                                           |
| `highlight`      | `span_id`, `highlight_text`    | Queues a canvas highlight command for an existing block or phrase.                                                                        |
| `record_gate`    | `gate_id`, `status`, `reason`  | Persists the learning-gate decision for the lecture.                                                                                      |
| `remember`       | `note`, optional `scope`       | Appends durable learner memory and a trace record. `scope=global` writes cross-course memory; `scope=course` writes active-course memory. |
| `generate_image` | `prompt`, `section_id`         | Stores a raster infographic asset in the learner workspace.                                                                               |

Every tool response is structured as `{ "ok": true, ... }` or
`{ "ok": false, "error": "..." }`; failed tools are sent back to the model so it
can recover without pretending the action happened.

## Canvas Commands

The final tutor turn can also return product-level canvas commands:

- `focus_section`: scroll to a section.
- `highlight_span`: highlight a block or phrase.
- `append_section` / `update_section`: materialize learner-specific sections.

Low-level `write` and `edit` are the preferred durable path. Product-level
append/update commands compile into the same student canvas overlay rather than
mutating official course material.

## UI Activity Tags

The backend emits streaming `activity` events only when a real harness step or
tool execution happens. The frontend displays the latest compact tags outside
the assistant message, for example:

```txt
write: /lecture/canvas/student/tool-loop-note.md
record_gate: bayes-risk-check
focus: losses-and-risks
highlight: losses-and-risks-p-1
```

Assistant prose is not parsed as a tool call.

## Regression Proof

The end-to-end backend regression is
`apps/api/tests/test_agent_tool_e2e.py`. It streams a real tool loop, writes a
student Markdown section, persists memory, records a gate, emits focus/highlight
activity tags, reloads the student canvas through the API, and verifies the
memory is loaded into a later tutor turn.
