# Before you begin predictions

A prediction is an optional first guess before a new concept. It is distinct
from a checkpoint: it never passes a gate, awards mastery or unlocks content.
The rest of the canvas stays accessible. Saving an answer does not trigger an
LLM call or immediate grading.

## Authoring and review

New canvas authoring may include at most one source-grounded prediction per
lecture, before its relevant explanation. Avoid duplicating an approved
initial diagnostic. Professor draft preview displays the card without a
learner answer form. Existing publications are not rewritten automatically.

```markdown
<!-- block id="generalization-prediction" type="prediction" -->

:::prediction Before you begin
A model classifies every training example correctly. What do you expect on
new examples, and why?
:::
```

## Learner state

`GET/POST /courses/{course}/lectures/{lecture}/predictions` uses the ordinary
authenticated learner or isolated professor-preview identity. POST accepts
`block_id`, `publication_version` and `answer`; null means skip.

Private JSON files live under
`users/<user-key>/courses/<course>/lectures/<lecture>/predictions/`.
The backend owns section, question, block digest, publication version and save
time. A saved first answer or skip cannot be rewritten for the same question
and publication. Repeating the identical submission is idempotent. A new
publication requires a fresh response; stale responses are not displayed or
sent to the tutor. A later response replaces the old private file for that
block. Course-workspace reset and account deletion remove this state.

The tutor receives current predictions as untrusted learner context and is
instructed to invite a guess before teaching and revisit it after explanation.
Skipping is respected. This conversational timing is agent guidance, not a
mandatory sequence or an efficacy claim. Prediction access and tutor context
are disabled during independent-exit and delayed-transfer attempts.

The frontend uses `PredictionBlock`, `LessonPredictions` and `PredictionContext`.
The backend separates models, private storage and routes in the
`canvas_prediction*` modules. No prediction answers enter professor analytics.
