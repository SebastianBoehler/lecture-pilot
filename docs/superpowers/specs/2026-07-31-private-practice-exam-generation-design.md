# Private Practice Exam Generation

## Goal

Add a learner-only flow that generates one source-grounded practice exam and
offers the same immutable exam as an interactive web form and a print- or
tablet-ready PDF. A standard exam contains 25 mixed multiple-choice and
open-ended questions, with a supported range of 20–30 questions.

Exam generation uses currently unlocked, published course canvases. A learner
may optionally enrich the exam pattern with privately retained PPI exam
protocols. PPI material can influence coverage, question style, expected depth,
and difficulty, but official course material remains the authority for factual
content and correct answers.

## Product Boundary

Practice exams are separate from the existing Exam Readiness check:

- Exam Readiness remains a short formative diagnosis with evaluation and a
  revision plan.
- Practice Exam Generation creates a longer exam simulation without hints or
  correctness feedback.
- The first release does not grade, submit, score, reveal solutions, ingest
  completed scans, or update readiness progress.

The generated exam is useful when completed in the browser, printed on paper,
or annotated as a PDF on a tablet. How completed work later returns to
LecturePilot is deliberately deferred.

## Canonical Exam Contract

Generation produces one private `PracticeExam` object. The web and PDF
renderers consume public projections of this object; they never generate their
own questions.

The private object contains:

- stable exam and question IDs;
- course ID, language, title, instructions, duration, creation time, and total
  points;
- the IDs and revision fingerprints of every source used;
- ordered multiple-choice and open-ended questions;
- per-question points, difficulty, and authoritative course source anchors;
- multiple-choice answer indices and concise open-answer rubrics for generation
  validation and possible future grading; and
- PPI pattern provenance without making PPI a factual answer source.

The learner-facing projection omits answer indices, rubrics, rationales,
quality-review notes, internal paths, and source excerpts. The exam UI and PDF
must expose the same ordered questions, options, points, instructions, and
duration.

An exam is immutable after successful generation. Regeneration creates a new
exam ID rather than modifying an earlier attempt.

## Learner-Owned Storage

Private exam data stays below the authenticated learner's hashed workspace:

```txt
users/<user-key>/courses/<course-id>/
  exam-sources/ppi/<ppi-lecture-id>/
    manifest.json
    source.zip
    normalized/
  practice-exam-generations/<request-key-hash>.json
  practice-exams/<exam-id>/
    exam.json
    exam.pdf
```

PPI sources never enter `courses/<tenant>/<course>/source`, published canvases,
professor builder state, or another learner's workspace. Professors, platform
administrators, and other learners cannot read them through an API.

Each PPI manifest records the PPI lecture ID and title, protocol count,
download timestamp, upstream `borrowed_until` value, accepted filenames,
content hashes, normalization status, and source revision. The raw ZIP and
normalized private material remain usable indefinitely. They are removed only
when the learner deletes that source, resets the course workspace, or deletes
the account. Upstream expiry controls re-download availability, not local reuse.

Practice exam deletion removes only the selected immutable exam and its cached
PDF. Source deletion must be explicit and must not silently delete previously
generated exams.

## PPI Import Flow

LecturePilot uses the pinned `tue-api-wrapper` SDK directly inside the backend.
It does not call the wrapper's environment-credential FastAPI routes because
PPI credentials belong to the active learner.

1. The setup screen lists already retained PPI sources first. Reusing one
   requires no credentials or PPI request.
2. `Connect PPI` explains that PPI has a separate password and keeps the entered
   values in browser memory only while the dialog is open.
3. The backend creates a short-lived `PpiClient`, authenticates, retrieves the
   catalog and borrowed page, returns bounded catalog metadata, and closes the
   client. The password uses `SecretStr` at the request boundary.
4. The learner selects one exact PPI lecture. LecturePilot does not borrow based
   on automatic title matching.
5. If the lecture is already borrowed, the backend downloads it without a
   borrow request or token warning.
6. If it is not borrowed, LecturePilot shows the lecture, protocol count,
   current token balance, one-token cost, and four-week upstream access period.
   A request must include explicit `confirm_token_spend=true`. The backend
   rechecks current state before borrowing so stale browser state cannot spend
   a token accidentally.
7. The ZIP is downloaded, validated, normalized, and published atomically into
   the learner source directory. Credentials and the PPI session are discarded.

The import accepts only regular `.pdf` and `.txt` protocol files. It rejects
absolute paths, traversal, hidden paths, symlinks, duplicate normalized paths,
unsupported suffixes, excessive file counts, oversized compressed or expanded
content, and invalid PDFs. Partial imports do not become visible.

If a selected PPI source cannot be imported, generation stops with a clear
error. LecturePilot does not silently omit it and proceed with course material
alone.

## Generation Pipeline

1. Authorize the current learner against the requested course.
2. Resolve only published lectures that are currently unlocked for that
   learner. Future or hidden material cannot enter the prompt.
3. Read the selected private PPI source manifests and normalized text through
   server-derived paths.
4. Build a typed blueprint allocating question type, points, difficulty, and
   authoritative course anchors across the available lectures. PPI evidence may
   affect the distribution but cannot be the sole anchor for a question.
5. Generate questions in bounded batches using structured provider output.
   Each batch receives only the relevant course excerpts and bounded PPI pattern
   evidence. Questions must be newly authored; raw protocol passages and
   remembered questions are not reproduced verbatim.
6. Validate counts, point totals, source anchors, unique IDs, option counts,
   answer indices, question length, and duplicate prompts deterministically.
7. Run a bounded source-grounding review against the official course excerpts.
   Invalid questions receive targeted repair; unresolved errors fail the job.
8. Atomically persist the immutable exam and source fingerprint.

Generation uses the existing idempotent, recoverable generation-record pattern.
There is no mock exam, reduced-quality fallback, or partially valid result. A
retry with the same idempotency key recovers the same job; requesting a new exam
uses a new key and produces a new exam ID.

## PDF Rendering

The PDF is derived from the stored public exam projection on first download and
then cached under the exam directory. The API owns a fixed LaTeX template and
escapes every generated value. Model output is never treated as executable TeX.

The template includes the exam title, instructions, duration, total points,
page numbering, student-name fields, multiple-choice boxes, and proportional
writing space for open-ended questions. It excludes solutions, rubrics, source
references, and PPI provenance.

Compilation runs only through the existing isolated compiler service. A PDF
failure leaves the valid online exam intact, reports the compiler error, and
can be retried without regenerating questions.

## API Surface

All routes require the current learner session, CSRF protection for mutations,
and exact course access.

- `GET /courses/{course}/ppi-exam-sources`: list retained private sources.
- `POST /courses/{course}/ppi-exam-sources/catalog`: authenticate and inspect
  bounded PPI metadata without mutation.
- `POST /courses/{course}/ppi-exam-sources/imports`: download an existing
  entitlement or explicitly confirm and perform a borrow before download.
- `DELETE /courses/{course}/ppi-exam-sources/{source}`: delete one private
  retained source.
- `GET /courses/{course}/practice-exams`: list the learner's exams.
- `POST /courses/{course}/practice-exam-generations`: generate an exam with an
  idempotency key, selected retained PPI source IDs, question count, and
  duration.
- `GET /courses/{course}/practice-exam-generations/status`: recover the
  generation status and completed exam ID after an interrupted request by
  supplying the same idempotency key.
- `GET /courses/{course}/practice-exams/{exam}`: return the public exam.
- `GET /courses/{course}/practice-exams/{exam}/pdf`: compile or return the
  cached authenticated PDF.
- `DELETE /courses/{course}/practice-exams/{exam}`: delete one exam.

IDs supplied by the browser are selectors only. The backend derives tenant,
learner, course authority, and every filesystem root from the active session.

## Web Flow

Add a separate `Practice exam` surface beside, not inside, Exam Readiness.

1. `Generate practice exam` opens a compact setup dialog.
2. Course material is always selected. The learner may choose retained PPI
   sources or select `Connect PPI` to import one.
3. The setup offers 20–30 questions with 25 selected initially and a 90-minute
   duration initially. It does not expose model or generation settings.
4. `Generate exam` shows a source-grounded generation state and keeps the
   idempotency key for recovery.
5. A completed exam opens as a focused online exam with visible progress,
   points, question navigation, multiple-choice controls, and open text fields.
   Responses remain in tab-scoped browser session storage so a refresh does not
   erase the active exam. They are not sent to the backend or graded in this
   release. Logout, account replacement, and exam deletion clear the matching
   response draft.
6. `Download PDF` retrieves the authenticated cached rendering. `Delete exam`
   and `Delete PPI source` use consequence-specific confirmations.

The exam library distinguishes online-ready and PDF-generation failures. Empty
states point to `Generate practice exam`. PPI errors explain whether the learner
must correct credentials, obtain tokens, choose another lecture, or retry a
temporary upstream failure.

All new copy is localized in English and German, uses sentence case, and keeps
`Exam readiness check` and `Practice exam` as distinct terms.

## Security And Observability

- Never persist or log PPI credentials, PPI cookies, raw protocol text, learner
  answers on the backend, model prompts, rubrics, or watermarked user
  identifiers.
- Preserve upstream watermarks in retained originals; never expose raw protocol
  downloads through shared course-asset routes.
- Record metadata-only events for catalog access, import outcome, token-spend
  confirmation, generation stage, source counts, provider/model usage, PDF
  outcome, and deletion.
- Apply existing learner quotas plus explicit compressed, expanded, file-count,
  normalized-text, model-context, exam-count, and PDF limits.
- A PPI token may be spent only inside the confirmed import request. Retries
  first recheck whether the lecture is already borrowed.

## Error Handling

Errors preserve the last safe state and state the next action:

- invalid PPI credentials: correct the PPI-specific credentials;
- no tokens: obtain a token or select an already borrowed lecture;
- stale token confirmation: refresh the catalog and confirm the current state;
- unsafe or unreadable archive: no source is retained;
- insufficient unlocked source coverage: publish or unlock more course material;
- provider or validation failure: retry generation without creating an exam;
- compiler failure: continue online or retry the PDF download; and
- quota exhaustion: delete an existing private source or exam before retrying.

## Verification And Success Checks

- Unit-test the exam schema, public projection, blueprint validation,
  source-grounding rules, duplicate detection, and LaTeX escaping.
- Test PPI catalog/import with a fake SDK client for cached, already borrowed,
  confirmed borrow, rejected unconfirmed borrow, no-token, authentication, and
  upstream-failure paths.
- Test ZIP traversal, symlink, hidden-file, type, count, compressed-size,
  expanded-size, duplicate-path, and atomic-publication boundaries.
- Test learner isolation, enrollment, unlock enforcement, CSRF, deletion, and
  the absence of professor or administrator access.
- Test that web and PDF projections have the same question order and content and
  that neither exposes private authoring data.
- Test the web setup, cached-source reuse, token confirmation, generation
  recovery, online exam, PDF download, empty states, and errors in English and
  German.
- Run the narrow API/web suites, then `npm run verify:api` and
  `npm run verify:web`.
- Verify the complete changed workflow at `http://127.0.0.1:5173`, including an
  online exam, a generated PDF, responsive layout, keyboard use, and no console
  errors.

The feature is complete when an enrolled learner can generate a validated exam
from unlocked course material, optionally reuse or privately import one PPI
lecture, complete the identical exam online, and download a valid print-ready
PDF without exposing private inputs or spending an unconfirmed token.
