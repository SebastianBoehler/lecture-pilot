"""Shared authoring guidance; source and professor approval remain authoritative."""


def capability_design_instruction() -> str:
    return (
        "Separate disciplinary capabilities from logistics: agendas, contact details, feedback "
        "QR codes and advertised course goals are context, not substantive mastery targets. "
        "For each capability identify the observable operation (discriminate, explain, calculate, "
        "derive, trace code or construct), then specify atomic evidence before writing tasks. "
        "Supply necessary givens and permitted aids without supplying the knowledge being assessed. "
        "Write fully instantiated tasks, not instructions to a future question writer: provide "
        "the actual environment, observations, numerical values, table or code needed to answer. "
        "A reference to unspecified data is not a usable task. Required criteria must cover every "
        "part of the outcome and invariant, including explicit boundary conditions; optional "
        "criteria are enrichment only. "
        "Before returning, solve every concrete task to check numerical consistency, dimensions, "
        "and whether its instances actually expose every required criterion. Avoid degenerate "
        "cases that omit the error types or boundary distinctions being assessed. Hints support "
        "the baseline task or an explicitly different analogy; never reuse hidden exit or "
        "delayed-transfer givens or solutions in the hint ladder. "
        "Calibrate language and support to evidenced learner level and prerequisites; never infer "
        "expertise from attendance or confidence. Keep the invariant and evidence standard fixed. "
        "A constructed misconception is a diagnostic hypothesis, not an observed student error. "
        "Changing wording alone does not establish equivalent difficulty or transfer. "
    )


def canvas_teaching_instruction() -> str:
    return (
        "Include at most one optional prediction card per lecture before a suitable new concept, "
        "only when a concrete guess can prepare the learner for the explanation that follows. "
        "Use <!-- block id=\"concept-prediction\" type=\"prediction\" --> followed by "
        ":::prediction Before you begin\n[a concrete source-grounded prediction question asking why]\n:::. "
        "Replace the bracketed text with the actual question; do not include its answer in the card. "
        "This is ungraded and skippable, not an approved checkpoint or hidden assessment. "
        "Do not duplicate an existing diagnostic or add one to administrative sections. "
        "Use a short, concept-specific section title, never a filename or extracted page range. "
        "Select assessment format from the capability, not a quiz quota: use single-choice quizzes "
        "for meaningful discrimination/classification with one supported answer and diagnostic "
        "distractors; use open checkpoints for explanation, derivation, calculation, code tracing "
        "or construction. Quizzes complement, never replace, exact approved checkpoints. "
        "Avoid back-to-back quiz and checkpoint blocks, especially long tasks. Separate optional "
        "formative checks with source-grounded explanation, an analogous worked example or a "
        "meaningful transition; omit redundant optional checks instead of adding filler. "
        "When several approved diagnostics share a section, write a short orientation paragraph "
        "for each using block id check-context-<target_id> and type paragraph. Explain what the "
        "next task asks the learner to do or how its purpose differs from the previous task, "
        "without hints, solutions or substantive teaching. The server places that paragraph "
        "immediately before its exact approved checkpoint. Orientation is not teaching coverage. "
        "Never delete, merge, shorten or rewrite approved tasks to improve spacing. "
        "Place canonical practice-* diagnostics before substantive help on that capability. "
        "Then use an analogous worked example when useful and a later formative check; do not "
        "require a prediction or principle explanation at every step. Use one selectively when "
        "it exposes the intended relationship: inspect the givens, predict, reveal one change, "
        "then explain why. If prerequisites are missing, teach an analogous worked example "
        "first and progressively return reasoning to the learner. These teaching activities "
        "must not expose hidden assessment tasks or count as independent evidence. Do not "
        "treat the presence of a diagnostic as coverage: checkpoint text is not an explanation. "
        "Teach every source-supported method, distinction and formula needed for its required "
        "evidence, including later concepts in the supplied source packet. "
        "Do not reveal the diagnostic's solution in its givens or use the hidden exit task as an example. "
        "Use short capability-specific assessment captions for navigation. Administrative material "
        "must not become arbitrary recall questions; do not fabricate a teaching target to fill "
        "an evidence batch. Report insufficient disciplinary evidence for review. "
        "Use media only when it supports the concept, without duplicate assets or decorative "
        "slide quotas. Keep source provenance exact. Captions must describe source-supported "
        "content; a feedback QR slide is not a concept summary. If the available evidence cannot "
        "establish an image's meaning, retain its neutral source caption rather than guess. "
    )


def media_review_instruction() -> str:
    return (
        "Treat a caption/source mismatch as a factual error, including relabeling administrative "
        "media as disciplinary evidence. Check it against the available source content, not "
        "just an opaque filename; do not claim visual verification when no visual evidence is "
        "provided. Neutral source-provenance captions are valid. "
        "For interactive teaching, verify that the displayed values, units and explanations "
        "support the intended prediction or principle explanation. Do not demand extra clicks "
        "or questions as a quota: interaction alone is not evidence of understanding. "
        "Review assessment flow: flag consecutive long tasks with no meaningful orientation "
        "or redundant optional quizzes beside an approved checkpoint. Repair surrounding "
        "context, never approved task wording. Orientation before diagnostics must not reveal "
        "answers or count as substantive instruction. "
    )


def source_explanation_instruction() -> str:
    return (
        "Source grounding is not verbatim-only teaching. Explanations may unpack the standard "
        "meaning of concepts explicitly named in the source, derive consequences from its "
        "formulas or definitions, and work through new numerical examples of its methods. "
        "Check that reasoning and its assumptions; absence of the exact explanatory sentence "
        "from terse lecture slides is not by itself an unsupported claim. Preserve qualifications "
        "such as typical behavior versus a universal guarantee. Do not introduce unrelated "
        "topics, empirical findings, historical claims or incompatible definitions. "
        "Apply this same boundary to both requested teaching repairs and their later review: "
        "do not demand an explanation and then reject it solely for not being quoted in the "
        "source. If a protected assessment genuinely requires knowledge outside these bounds, "
        "report the design conflict rather than repeatedly adding and removing that teaching. "
    )
