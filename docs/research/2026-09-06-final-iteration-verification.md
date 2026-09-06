# Final iteration: implementation and presentation record

6 September 2026. Implements the bounded changes proposed in
[the research report](2026-09-06-research-to-presentation-freeze.md).
Implemented through `a89567c` from baseline `cb4f771`; publishing this code does not
imply a new deployment.

## Implemented

- Shared authoring and media-review guidance now asks for selective prediction
  and principle explanation, checks values/units against the intended relationship,
  and introduces analogous worked examples when prerequisites are missing.
  Teaching interactions must not expose hidden assessments or count as independent
  evidence. The learner study guide now explains when to start with a worked example.
- The gate benchmark uses explicit checkpoint submissions with a task, stage,
  gate revision, issuance timestamp, source, rubric and computed map revision.
  Fixtures live in `scripts/gate_benchmark_cases.py`; the runner separates grading
  disagreements from provider and contract failures. These are author-written
  fixtures, not published-course approvals or a learner efficacy study.
- Tutor activity is a collapsed per-turn timeline with expandable real action
  details. It retains streamed actions when the final answer arrives. No synthetic
  mode calls, durations or success indicators are shown. Session goal and model
  move into a disclosure. Pending work has one status line.
- The flat composer supports multiline input, IME-safe Enter, duplicate-send
  protection, error announcements and draft restoration after a rejected send.
  Its visible label is removed; its accessible name remains. Scrolling up stops
  automatic following and exposes a return-to-latest action.
- Focused attempts retain their learning-access restrictions. Submit and help
  share an aligned action row; progress is consolidated in the outline. Language controls
  are styled, the professor header offset is corrected, and mobile dialog focus
  follows breakpoint changes and includes disclosure summaries.

The visual direction adapts the compact disclosure pattern in
[assistant-ui's tool timeline](https://www.assistant-ui.com/elements/tool-timeline)
and [tool call](https://www.assistant-ui.com/elements/tool-call), using the existing
components and theme tokens without a dependency migration.

## Sidebar consolidation after user review

The learner rail now has three entries: Tutor, Document outline, and files.
The former learning path and Source notes panels were removed, including the
misleading timeline-gate metadata and its hard-coded source-path placeholder.
The outline uses the already reconciled learner state, with no additional
learning-map request. It owns section/check/figure navigation, the current goal,
a shortcut to the pending check, and plain-language evidence labels. With-help,
independent and delayed demonstrations remain distinct; no mastery percentage
or prerequisite lock is inferred from navigation history.

“How practice works” explains that reading order is free, assessments are handled
one at a time, and independent attempts temporarily close materials and chat.
The duplicate evidence inventory above the canvas was removed. Current assistance,
focused-attempt access, and task-bank warnings remain visible where they matter.

The file panel places the selected source preview first and collapses its technical
tree behind “Browse files”. Headers use 16px, navigation/messages 14px, and status
labels 12px. Outline labels strip Markdown delimiters and retain enough task wording
to distinguish checks. Deleted path/notes strings and styles were removed.

The language context is now separate from translation data, preserving its identity
through development hot updates. A translation edit was verified live without
blanking the page. Outline navigation, the pending-check shortcut, mobile focus,
desktop/modal breakpoint changes, source preview placement, and both themes were
rechecked in the actual published lecture. A transient learner-state fetch failure
on opening a separate verification tab failed closed and recovered after reload.

## Live assessment observations

Model: `openai/gpt-5.6-luna`, using the current checkpoint harness.
The first 10-case run matched 9 expected outcomes: zero false passes, one apparent
false rejection, zero contract failures and zero provider failures.
On review, the disputed paraphrase did not explicitly say what the classifier
predicts. The fixture now states that it predicts a category for each input;
that single revised case passed on rerun. The other nine cases were unchanged.
Do not describe this as a fresh 10/10 run or an estimate of population accuracy.
Cases include incomplete answers, alternate wording, misleading vocabulary and
incorrect reasoning about thresholds or error costs.

The deterministic API suite verifies persisted support, task exposure, fresh-task
selection, stale bindings, reload recovery and the structured checkpoint contract.
It does not establish the semantic quality of every generated task.

## Final verification

- Full web suite: **398 tests passed in 127 files**, serial run. Three unrelated
  tests had failed in a parallel run, passed on targeted serial rerun, and passed
  in this full serial run. The earlier incompatible UI assertions were updated
  to check the intentional disclosure and activity behavior.
- Targeted API suite: **43 passed**, covering teaching guidance, benchmark
  bindings, checkpoint assessment and persisted learning-state transitions.
- TypeScript/Vite production build, ESLint, Ruff, dead-code checks, changed-file
  formatting and whitespace checks passed. The build reports its existing large
  math-rendering chunk warning.
- The combined `verify:web` command stopped at formatting of the unrelated
  `2026-09-06-production-testing-usage.md`; the remaining checks were run separately.
  That report was formatted before committing this iteration; the complete
  `verify:fast` quality check then passed.
  The full API/compiler/converter suites were not rerun for this narrow change.
- Private logs and a SHA-256 manifest of the changed code/test files and the
  publication are saved in `.journal/final-iteration-2026-09-06/` (gitignored).

## Presentation content and environment

Use **Grundlagen des Maschinellen Lernens Vorlesung**, lecture 01,
**Introduction to Machine Learning**, publication **1**, canonical English wording.
The language control reports no recorded assessment-language metadata; no translated
variant was selected or invented. The private publication manifest records:

- Published: `2026-09-06T02:03:08.129349Z`
- Source revision: `ad3428fc9f07b83c6cf74dffa4bef88c56e0d36f84e37bfdf1762d2cbf7d2683`
- Practice design: `74ab96ede2e207299988af7aaea6d5f1f282c25d46d514523d1ec9787646f03b`
- Learning map: `09ea38f1795dcc4d9bdec0bd20196c3113c9f04922a62c5c2b983c962e979033`

The active rehearsal frontend is port 5173 and uses API port **8001**.
The API is the existing private `output/hardening-2026-09-06/runtime.py` runtime,
with data under `output/overnight-2026-09-06/workspaces`, normal provider limits
and private response capture. The `.env.local` default port 8000 is not this
running rehearsal. No running/queued status was found in this course's authoring
metrics, generations or generation ownership records during the final check.

The current published canvas was not regenerated. Its supervised-learning passage
and original slide were inspected together: the highlighted explanation maps an
input to a desired output; the tutor's hint distinguishes input, label and learned
mapping. The existing rectangle/loss example also states its data, inclusive
boundaries, predictions and error calculation. This is a source/teaching consistency
review, not evidence that a learner understood the material.

## Rehearsal evidence and remaining limits

- The actual focused checkpoint hid teaching/chat. Requesting help first showed
  “Recording help…” and then reopened materials. Its supported state survived reload.
- A real chat request produced focus, highlight and phrase actions, each visible
  in the retained timeline, and highlighted the intended supervised-learning passage.
- The source reference opened inside the app. The PDF reference provides its page
  trace; its linked original slide loaded as an image in the file preview.
- Desktop clipping was measured at the reported 1073 × 1035 CSS viewport. The
  composer ended about 18 pixels above the bottom. A temporary narrow viewport
  verified close/reopen, disclosure access and composer bounds. Light/dark colors
  were checked; the viewport override and light mode were restored.
- Development hot replacement produced context/effect warnings while files changed.
  Reload restored the page; the later context split prevents recreation on translation
  updates. These observations do not claim a production crash.
- Composer provider-error UI is verified with a rejected request in component
  tests. A live provider outage was not injected into the shared rehearsal runtime.
- **The current private preview has exhausted its reviewed task bank.** The app
  correctly leaves it supported and asks for a new reviewed task. Existing learner
  work was not reset. Do not promise a fresh independent attempt in this already
  exposed preview. Use an unexposed learner session for that demonstration, or show
  the tested transition and explain this limit. No delayed review was fast-forwarded.

## Annotation direction after the presentation

A useful next feature is a private annotation tied to a passage: quoted text,
section/block identity, source/publication revision, author and a short explanation
or learner interpretation. Selecting the annotation should focus its passage.
Source changes should mark it for review, not silently reattach it to unrelated text.
Store lecture notes in the learner overlay; promote only broader teaching preferences
into cross-course memory. Keep annotations unavailable during an independent attempt.
This design is recorded for the next iteration; annotations were not implemented here.
