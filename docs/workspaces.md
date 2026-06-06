# Workspace Storage

LecturePilot uses a private course source plus per-student overlays.

```txt
course source root
  Lecture03-eng.tex
  images/...

.lecturepilot/workspaces
  students/<hashed-user-id>/courses/<course-id>/lectures/<lecture-id>/canvas.json
```

The course source root is configured with `LECTUREPILOT_COURSE_MATERIAL_ROOT`.
For local development it can point at the private Overleaf checkout. Professor
material stays outside the public repository and the generated `.lecturepilot/`
workspace is gitignored.

## Canvas Import

On first open, the API imports the lecture LaTeX into a typed `CanvasDocument`.
The importer does not expose every Beamer frame as a page. It groups related
frames into study sections, keeps official figures and formulas, and writes the
result into the student's workspace. Later agent commands can append or update
sections, so personalized explanations, examples, diagrams, or quiz blocks
remain scoped to that learner.

The current implementation imports Lecture 03 from `Lecture03-eng.tex` and
serves only browser-safe image assets from the course material root. The web
canvas renders preserved TeX formulas with KaTeX.

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
Markdown/text/JSON: 2-5 MB
PDF: 100 MB
Images: 20 MB
```

The API rejects hidden paths, absolute paths, `..` traversal, unsupported file
types, and oversized payloads. Production deployments should back this with
object storage, tenant quotas, audit logs, malware scanning for uploads, and
short-lived signed URLs for protected assets.
