# Workspace Storage

LecturePilot uses a private course source plus per-student overlays.

```txt
course source root
  Lecture03-eng.tex
  images/...
  videos/...
  code/...

.lecturepilot/workspaces
  students/<hashed-user-id>/courses/<course-id>/lectures/<lecture-id>/
    canvas/
      index.md
      sections/
        01-decision-making-under-uncertainty.md
        02-bayes-formula.md
      student/
        90-student-soccer-bayes-example.md
    canvas.json
```

The course source root is configured with `LECTUREPILOT_COURSE_MATERIAL_ROOT`.
For local development, keep the private course slice in
`local-course-materials/martius-ml`; the API prefers that repo-local folder
when no environment variable is set. Professor material stays outside git, and
the generated `.lecturepilot/` workspace is gitignored.

For Overleaf-backed courses, copy or sync the full professor checkout into that
gitignored root, excluding only `.git/`. The source bundle scanner keeps the
professor's folder structure and classifies TeX, Markdown/text, CSV/JSON, PDF,
images, SVG, videos, Python code, and notebooks as course source artifacts.
The API exposes the current scan through
`GET /courses/{course_id}/source-bundle` for future professor/admin tooling.

## Course Material Resolver

The target resolver should be filesystem-first, with manifests as the stable
contract and folder names as convenient defaults:

```txt
local-course-materials/
  martius-ml/
    course.json
    lectures/
      lecture-03/
        lecture.json
        sources/
          Lecture03-eng.tex
          images/
            Ch3/spam-DALL-E.jpg
            Ch3/Venn_C-X_1.pdf
        canvas/
          index.md
          sections/
            01-decision-making-under-uncertainty.md
            02-bayes-formula.md
          assets/
        coverage.json
```

`course.json` should hold stable ids, title aliases, term, teacher metadata, and
matching hints for Alma/TUE API course discovery. `lecture.json` should hold the
lecture id, date, title, source files, published status, and canvas entrypoint.

The resolver flow is intentionally simple:

1. Scan `local-course-materials/*/course.json`.
2. Match the student's enrolled courses by stable id first, then normalized
   title aliases.
3. Scan `lectures/*/lecture.json` for the matched course.
4. Expose only lectures with `date <= today` and `published=true`.
5. Load `canvas/index.md` when it exists.
6. If no canvas exists but sources exist, run the ingestion pipeline into a
   draft canvas for professor/admin review.

Original source files remain immutable evidence. The base canvas is the
professor-approved learning document derived from those sources. Student
workspaces only store private overlays, progress, and generated additions.

## Canvas Import

On first open today, the API can import the lecture LaTeX into Markdown section
files as a bootstrap path. The target workflow is the long-context LLM ingestion
pipeline described in [course-ingestion-pipeline.md](course-ingestion-pipeline.md):
upload sources, generate a draft canvas, stage optional videos or generated
infographics, and require professor approval before publishing.

The canvas schema should not clip lecture coverage by arbitrary item, block, or
section counts. Operational quotas still belong at the file-storage and upload
policy layer.

The current LaTeX importer groups related frames into study sections, keeps
official figures and formulas, and writes the result into `canvas/sections/*.md`.
The API then compiles the Markdown directory into the typed `CanvasDocument`
that the web UI renders.

Later agent commands append or update files in `canvas/student/*.md`, so
personalized explanations, examples, diagrams, or quiz blocks remain scoped to
that learner. `canvas.json` is only a compiled cache and API artifact; it is not
the editable source of truth.

The current implementation maps the demo lectures to `Lecture01-eng.tex`,
`Lecture02-eng.tex`, and `Lecture03-eng.tex`, serves browser-renderable course
assets, and renders single-page PDF figures through generated PNG previews so
the learning canvas does not show browser PDF controls. The web canvas renders
preserved TeX formulas with KaTeX.

## Student Scope

Raw usernames are not used in filesystem paths. The workspace path uses a short
SHA-256 prefix derived from the authenticated user id. This is not a full GDPR
design by itself, but it keeps local storage keys pseudonymous and gives the
production design a clear place for retention, export, deletion, and quota
hooks.

## File Policy

Generated learner files are limited to typed study artifacts:

```txt
Markdown: 5 MB
Text: 2 MB
JSON: 2 MB
PNG/JPG/JPEG/WEBP: 20 MB
SVG: 2 MB
```

Course uploads are stricter and should remain professor-controlled:

```txt
TeX: 10 MB
Markdown/text/CSV/JSON: 2-5 MB
PDF: 100 MB
Images/SVG/GIF: 2-20 MB
Videos: 500 MB
Python/notebooks: 5-20 MB
```

The API rejects hidden paths, absolute paths, `..` traversal, unsupported file
types, and oversized payloads. Production deployments should back this with
object storage, tenant quotas, audit logs, malware scanning for uploads, and
short-lived signed URLs for protected assets.
