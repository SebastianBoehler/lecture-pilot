# Practice-exam correctness benchmark

Practice-exam generation uses unlocked published canvas evidence. A separate
review call receives the same bounded passages and a candidate with its
multiple-choice keys removed. It independently solves each question and
checks scope, ambiguity, reference answers, and rubric criteria. Acceptance
requires agreement with the stored key, solution reasoning, and quotations
verified against that question's cited passages. A source ID alone cannot pass
this check. Standalone numeric options also reject exactly equivalent fractions
and decimals, including simple LaTeX fractions; general expressions still
require semantic review. Unsupported or contradictory reviews trigger the existing bounded
regeneration; exhausted repair returns an error instead of an exam.

This improves generation validation. Existing immutable exams keep their saved
keys. Open-ended submissions remain ungraded and use a separate reference
solution for self-review; this benchmark does not evaluate student grading.

## Private fixture

Keep fixtures and reports below the ignored `.lecturepilot/benchmarks/` root.
Reports contain course evidence and provider output and must never be committed.
A fixture is a JSON object with:

- `course_title`: the course name.
- `documents`: serialized `CanvasDocument` objects with exact, source-checked
  passages and stable lecture/section/block IDs.
- `candidate`: a serialized `PracticeExam` containing at least 20 questions.
- `gold`: a map from every question ID to `{ "valid": true|false, "category":
"..." }`, labelled independently before any provider run.
- Optional `source_metadata` and `ppi_sources` for page provenance and
  non-authoritative question-pattern challenges.

Include valid controls alongside wrong keys, wrong calculations, unsupported
reference answers, multiple correct options, and out-of-scope topics citing
otherwise valid source IDs. Check extracted formulas visually against the PDF;
text extraction can drop mathematical symbols.

## Run

The runner reads the canonical project environment and uses the real planner
and reviewer. Its model allowlist change exists only inside the benchmark
process. Provide verified USD prices per million tokens; there are no guessed
prices or provider substitutions.

```bash
python scripts/benchmark_practice_exams.py \
  --fixture .lecturepilot/benchmarks/nlp/fixture.json \
  --prices .lecturepilot/benchmarks/nlp/prices.json \
  --model openai/gpt-5.6-terra \
  --model openai/gpt-6-sol \
  --model openai/gpt-6.1-sol \
  --budget-usd 3 --generate \
  --output .lecturepilot/benchmarks/nlp/results.json
```

The prices object maps each exact model name to nonnegative `input`,
`cached_input`, and `output` rates. The runner estimates cost using actual
provider usage, discounts cached input, and counts output reasoning tokens
once. It reserves a conservative byte-based input bound, maximum output, and
one transport retry before each call; failed requests retain an unknown-cost
reserve. It saves completed model results after each model.

## Interpretation

The fixed-candidate result measures the combined reviewer and deterministic
acceptance contract against human labels. False accepts count invalid questions
that pass both; false rejections count valid questions that do not. Contract
errors include key disagreements, so an intentionally wrong key can cause an
expected rejection even when the reviewer correctly solves the question.

`--generate` additionally runs the actual generation, bounded repair, and
review pipeline. Its acceptance and timing are diagnostics, not independent
proof that every generated question is correct. Inspect its saved questions
against the source separately. Report fixed-review and generation costs and
latencies separately; they are different operations.

A small source slice and one run per model cannot establish whole-course
reliability, Safari behavior, or learning efficacy. Provider benchmarks belong
outside deterministic CI. Contract and cost-accounting regressions live in
`test_practice_exam_review.py` and `test_practice_exam_benchmark.py`.
