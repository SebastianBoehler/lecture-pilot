# Professor enablement and maintenance

LecturePilot adoption should not depend on a professor discovering the workflow
alone. The product combines a short in-app walkthrough with an optional live
introduction and recorded German and English end-to-end tutorials.

## Maintainer commitment

For the university pilot, the maintainer should publish a semester-level point
of contact and keep these responsibilities explicit:

- triage setup and ingestion defects;
- run the release verification and deployment checklist;
- keep supported-format and self-hosting documentation current;
- offer a 30-minute introduction for new teaching teams; and
- review the onboarding material at the start of each semester.

This is a service commitment, not a claim of round-the-clock support. A future
institutional handover needs at least one additional maintainer, documented VM
and backup access, and a rehearsed deployment and recovery procedure.

## Thirty-minute introduction

Use one synthetic or permission-cleared course folder. Do not use private
student work or unapproved professor material in a shared call or recording.

| Time  | Outcome                                                                   |
| ----- | ------------------------------------------------------------------------- |
| 0–3   | Explain source ownership, private drafts, and publication boundaries      |
| 3–8   | Create the course and select language, access, and generation scope       |
| 8–13  | Upload a mixed folder and read rejected/converted/OCR-needed statuses     |
| 13–18 | Review the proposed lecture schedule and source assignments               |
| 18–24 | Generate one lecture and inspect slides, tables, links, and source traces |
| 24–27 | Edit, regenerate, and preview the exact learner canvas                    |
| 27–30 | Publish deliberately; show updates, analytics, help, and support          |

The professor should leave able to complete the path without the maintainer:
upload, inspect, accept or edit assignments, generate, preview, and publish.

## German and English recordings

Record the same canonical flow twice instead of dubbing one language. Use the
same demo folder and chapter boundaries so screenshots and support references
remain comparable.

1. What LecturePilot does and does not publish automatically
2. Course setup and exact Alma or ILIAS course naming
3. Whole-folder upload and file processing states
4. Schedule and source-assignment review
5. PowerPoint slides, spreadsheet tables, PDF OCR, code, and embedded links
6. Draft generation, learner preview, edits, and publication
7. Updating an existing course
8. Restarting the walkthrough and requesting support

Target 8–12 minutes per recording. Add captions and a transcript in the spoken
language, then verify the recording against the currently deployed release.
Show failure behavior as well as the happy path: unavailable autocomplete still
allows manual entry, rejected uploads name the reason, and unavailable OCR
preserves the original page.

## Product placement

The professor header already contains a persistent help action that restarts the
bilingual contextual walkthrough. It remains the canonical in-product entry
point. Once both recordings exist and have been checked against a release, add
their real URLs beside that action and at the upload, source-review, and publish
steps. Do not ship empty tutorial cards or placeholder links.

Every recording should state the release it demonstrates. Re-record only when a
workflow changes materially; otherwise update captions or a short release note.
