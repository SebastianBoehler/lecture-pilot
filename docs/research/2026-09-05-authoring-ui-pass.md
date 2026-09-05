# Automated authoring and navigation pass

5 September 2026. Implementation evidence, not a learner-efficacy evaluation.

## Reusable teaching procedure

The existing authoring flow remains source routing, professor-confirmed sources,
practice proposal and semantic critique, professor-approved design, generation,
revision-bound draft review, and publication. No approval stage was removed.

The shared instructions now explicitly work backward:

1. Separate disciplinary capabilities from logistics and advertised course goals.
2. Identify an observable operation and the invariant the learner must preserve.
3. Define atomic evidence of success before drafting questions.
4. Choose task format by capability, not equal quiz/checkpoint quotas.
5. Supply task givens and permitted aids without supplying assessed knowledge.
6. Calibrate support to evidenced learner context, not attendance or confidence.
7. Keep baseline, independent exit and delayed changed-form tasks distinct.

The canvas writer now receives the approved objective, learner context, scoped
outcome and invariant. It still does not receive hidden exit/transfer task text.
Unknown context stays unknown. Source anchors and semantic critique remain
necessary: a valid excerpt is not itself proof that an inference is supported.

## Concrete corrections

- Approved diagnostics can precede worked examples without being rejected by
  either generation validation or the publication learning-design report.
  Ordinary formative checks retain example-before-check ordering.
- Both canvas prompts use shared capability, assessment and media guidance.
- Caption/source mismatch is explicitly a factual-review concern. Text-only
  evidence cannot certify the meaning of an unseen image.
- Original-slide identity no longer depends on a writer preserving its caption;
  renamed slides count toward insertion capacity and are not inserted twice.
  An exact source PDF cover preview also represents that PDF's first slide.
- Section-cache version changed so resumed generation does not reuse old prompts.
- Professor navigation uses a second row at constrained desktop/tablet widths.
  The responsive selector is language-independent.
- Outline checks show task excerpts; original-slide labels omit long paths while
  retaining the complete caption as a tooltip and source access in the canvas.
  Distinct authored check titles are retained, and multiple checkpoints/quizzes
  in a section all appear instead of only the first one.
- Section navigation aligns the section start; individual blocks remain centered.
  Reduced-motion preference disables animated scrolling.

## Research rationale and limits

Preserving retrieval work rather than putting the answer in the question is a
design inference from retrieval-practice evidence. Roediger and Karpicke's prose
experiments found a different immediate-versus-delayed pattern for testing and
restudy; they did not evaluate this application or AI-authored mathematics tasks.
[Primary article](https://journals.sagepub.com/doi/10.1111/j.1467-9280.2006.01693.x).

Selective, accurate links between text and media are motivated by multimedia
integration research, including Scheiter and Eitel's 2015 work. The university
record identifies both as Tübingen authors. This motivates design choices; it is
not evidence that any arbitrary highlighting or additional media improves learning.
[Tübingen publication record](https://tobias-lib.uni-tuebingen.de/xmlui/handle/10900/66653).

## Observed provider sample

One existing approved ML lecture evidence batch was generated with the configured
`openai/gpt-5.6-luna`, without changing runtime models. Generation and deterministic
section checks took 27.507 seconds, including any internal section retry time.
This is one observation, not a latency percentile or course-cost estimate.

The output had a concept-specific title and preserved two exact approved
diagnostics before instruction. It retained neutral source-media captions but
included no supplementary quiz. Mixed-format quality, novice/expert calibration
and cross-discipline generalization are not established by this sample.

The sample's separate source-bound semantic review took 5.009 seconds and returned
no issues. This is a same-model critic check, not independent human validation.
The sample was saved privately, not published. Existing published course content
does not change merely because generation instructions change.

A separate corrected local demo draft passed source-bound review (6.116 seconds)
after removing the duplicate cover and repeated figure, removing a feedback slide
misused as teaching media, correcting the generalization caption and placement,
and correcting a lecture-plan/course-plan scope error. It also incorporates the
reviewed concept section and places the other canonical diagnostic before help.
The earlier draft is backed up privately; the published snapshot was verified
unchanged. New draft approval is still required before publication.

## Cross-subject prefill checks

Two frozen synthetic repository fixtures used the production proposal and
semantic-review path with the unchanged runtime model. No proposals were saved
as approved designs. These are smoke samples, not the repository's multi-model
benchmark and not learning outcomes.

- Physics, constant acceleration: 28.892 seconds; all eight critic dimensions
  passed in this sample.
- Biology, natural selection: 33.074 seconds; critical exit-equivalence and
  rubric-sufficiency concerns, plus leakage/difficulty warnings.
- After explicitly requiring instantiated givens and complete required criteria,
  one biology recheck took 42.045 seconds. Rubric sufficiency passed, but invented
  numerical conditions were inconsistent, producing critical equivalence and
  difficulty flags. Both attempts are retained privately.

This is evidence against claiming that a general prompt alone guarantees usable
cross-discipline tasks. More specific instructions can introduce a new defect;
keep critical semantic findings blocking approval. Future quality evaluation
should distinguish a qualitative causal task from an unnecessary numerical one.

## Verification

The backend suite passed 1,167 tests with a temporary, migrated, isolated Postgres
database. The subsequent PDF-cover regression and affected planner/reviewer tests
also passed (50 targeted tests in the final focused run). All 380 frontend tests passed; the production
build passed with the existing large math-chunk warning. Changed-file lint and
format checks passed. These are not claims of running every CI command.

The final pre-push rerun passed all 1,168 backend tests, five capacity-harness
tests, `verify:fast`, and the production web build. The default parallel web run
had four UI-test failures; those four files passed with two workers, then all
380 web tests passed with `--maxWorkers=2`. This indicates timing sensitivity,
not an unconditionally green default-parallel run. No test assertions were
weakened. The disposable database was stopped and removed after verification.

Browser checks covered professor header geometry at 1,062 pixels in English and
German and at 390 pixels, plus desktop visual inspection. Student section jumps
left the heading visible below the sticky header; the outline was inspected in
dark mode. No browser error entries were returned. Mobile geometry is not a
complete mobile visual/accessibility audit.

The all-teaching-sections checkpoint requirement remains. An administrative-only
evidence batch cannot become an assessed learning target just because a prompt
asks for a question; such material still needs source/design review.
Readable canvas ordering is not a sealed experimental baseline: students can
read ahead. Automated drafts and professor approval do not demonstrate efficacy.
