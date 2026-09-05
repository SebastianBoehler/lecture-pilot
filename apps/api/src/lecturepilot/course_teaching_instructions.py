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
        "Calibrate language and support to evidenced learner level and prerequisites; never infer "
        "expertise from attendance or confidence. Keep the invariant and evidence standard fixed. "
        "A constructed misconception is a diagnostic hypothesis, not an observed student error. "
        "Changing wording alone does not establish equivalent difficulty or transfer. "
    )


def canvas_teaching_instruction() -> str:
    return (
        "Use a short, concept-specific section title, never a filename or extracted page range. "
        "Select assessment format from the capability, not a quiz quota: use single-choice quizzes "
        "for meaningful discrimination/classification with one supported answer and diagnostic "
        "distractors; use open checkpoints for explanation, derivation, calculation, code tracing "
        "or construction. Quizzes complement, never replace, exact approved checkpoints. "
        "Place canonical practice-* diagnostics before substantive help on that capability. "
        "Then use an analogous worked example when useful and a later formative check; do not "
        "reveal the diagnostic's solution in its givens or use the hidden exit task as an example. "
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
    )
