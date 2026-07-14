# Workspace Storage

LecturePilot uses one shared course source/canvas plus private user memories
and per-lecture learner overlays.

```txt
.lecturepilot/
  courses/<tenant-id>/<course-id>/
    source/
      uploads/
      normalized/
      assets/
      source-index.json
    canvas/
      lectures/<lecture-id>/
        index.md
        sections/*.md
        assets/
      media/
    builder/
      drafts/
      review-state.json

  users/<hashed-user-id>/
    profile.json
    memories/
      global.md
      preferences.json
      memory-trace.jsonl
    courses/<course-id>/lectures/<lecture-id>/
      attendance.json
      gates.json
      tutor-state.json
      canvas/
        index.md
        sections/*.md
        student/*.md
        student-assets/*
      canvas.json
    courses/<course-id>/memories/
      course.md
      memory-trace.jsonl

  previews/professors/<hashed-preview-id>/
    memories/
    courses/<course-id>/

  cache/
    pdf-previews/
```

The default local workspace root is `.lecturepilot/`. It is gitignored.
Production can keep this logical layout while storing metadata in Postgres and
files in S3-compatible object storage such as MinIO.

## Source Roots

Professor material is private. The local demo source root is configured with
`LECTUREPILOT_COURSE_MATERIAL_ROOT`; when unset, the API still looks for a
repo-local private folder under `local-course-materials/` for demo use.

Professor uploads go to:

```txt
.lecturepilot/courses/<tenant-id>/<course-id>/source/uploads/
```

The source bundle endpoint scans uploaded course sources first and then the
private local course root for compatibility:

```txt
GET /courses/{course_id}/source-bundle
```

It classifies TeX, Markdown/text, CSV/JSON, PDF, images, SVG, videos, Python
code, and notebooks as course source artifacts.

## Course Canvas

The course planner writes professor-approved base canvases to:

```txt
.lecturepilot/courses/<tenant-id>/<course-id>/canvas/lectures/<lecture-id>/
  index.md
  sections/*.md
  assets/
```

Original source files remain immutable evidence. The base canvas is the
professor-approved learning document derived from those sources. It is shared by
students and should not contain private learner state.

If no approved course canvas exists, the API can still bootstrap from mapped
LaTeX source files. The long-context LLM ingestion pipeline described in
[course-ingestion-pipeline.md](course-ingestion-pipeline.md) is the target
course-creation path: upload sources, generate a draft canvas, stage optional
videos or generated infographics, and require professor approval before
publishing.

## Learner Workspace

Each student gets a pseudonymous user root:

```txt
.lecturepilot/users/<hashed-user-id>/
```

Raw usernames are not used in filesystem paths. The user root holds cross-course
memory:

```txt
profile.json
memories/global.md
memories/preferences.json
memories/memory-trace.jsonl
```

Course-specific memory lives beside the learner's course state:

```txt
courses/<course-id>/memories/course.md
courses/<course-id>/memories/memory-trace.jsonl
```

`memory-trace.jsonl` is append-only provenance for memory writes. Entries record
the memory scope, active course, lecture, tool name, note, and optional
preference change so tutor personalization is inspectable rather than hidden.

Lecture-specific state lives below the user/course/lecture intersection:

```txt
courses/<course-id>/lectures/<lecture-id>/
  attendance.json
  gates.json
  tutor-state.json
  canvas/
    index.md
    sections/*.md
    student/*.md
    student-assets/*
  canvas.json
```

Agent commands append or update `canvas/student/*.md`. Personalized generated
images are stored in `canvas/student-assets/`. `canvas.json` is a compiled API
cache and not the editable source of truth.

## Professor Learner Preview

A professor can open a published lecture in a private learner preview. Its
attendance, progress, canvas additions, tutor memory, and generated assets use
the same learner contracts but live under:

```txt
.lecturepilot/previews/professors/<hashed-preview-id>/
```

The preview identity is derived from the authenticated professor and course.
Only a course owner can request it. Preview activity is excluded from learner
and cohort analytics, while model and image usage remain attributed to the
professor account. Resetting the preview never deletes real student state.

Canvas section Markdown is intentionally close to the learning-app explainer
model: one section file is one stable teaching unit, and assets remain normal
file references. Supported section blocks are:

```md
Long narrative paragraph with **Markdown emphasis**, inline math, and source markers.

![Course image](asset:Ch3/spam-DALL-E.jpg)
![Generated learner image](/workspace-assets/<course>/<lecture>/<user-key>/student-assets/risk.jpg)
[Professor-approved video](https://youtu.be/12345678901)

| Action | Expected risk        |
| ------ | -------------------- |
| Reject | Prefer more evidence |

:::checkpoint Risk gate
Explain why changing a loss term can move the decision threshold.
:::

:::quiz Retrieval check
Which quantity directly changes the expected-risk decision?

- Posterior probability
- Slide number
- Font size
  :::
```

The parser also accepts explicit block comments such as
`<!-- block id="risk-table" type="table" -->` when a pipeline or agent needs a
stable block id for later focus/highlight commands.

## Agent Rules

The agent sees this filesystem image through typed tools only. It may use
`pwd`, `ls`, `find`, `grep`, and `read` to inspect authorized roots; `write` and
`edit` to update learner-owned Markdown/component/memory files; `focus` and
`highlight` to navigate the canvas; `generate_image` for raster infographics;
and `record_gate` plus `remember` for progress and personalization. It must not
freely traverse host paths, mutate official source files, duplicate large course
assets into learner folders, or reveal future lecture material.

## File Policy

Generated learner files are limited to typed study artifacts:

```txt
Markdown: 5 MB
Text: 2 MB
JSON: 2 MB
PNG/JPG/JPEG/WEBP: 20 MB
SVG: 2 MB
```

Course uploads are stricter and professor-controlled:

```txt
TeX: 10 MB
Markdown/text/CSV/JSON: 2-5 MB
PDF: 100 MB
Images/SVG/GIF: 2-20 MB
Videos: 500 MB
Python/notebooks: 5-20 MB
```

The API rejects hidden paths, absolute paths, `..` traversal, unsupported file
types, and oversized payloads. Production deployments should add object storage,
tenant quotas, audit logs, malware scanning, retention, deletion, and
short-lived signed URLs for protected assets.
