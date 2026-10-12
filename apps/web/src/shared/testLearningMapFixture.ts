export function learningMapPayload() {
  return {
    course_id: "martius-ml",
    lecture_id: "lecture-03",
    title: "Bayesian Decision Theory",
    objective: "Explain and apply Bayesian decision theory.",
    revision: "b".repeat(64),
    nodes: [
      {
        id: "bayesian-decision-theory-the-aim",
        title: "Decision making under uncertainty",
        lecture_id: "lecture-03",
        section_id: "bayesian-decision-theory-the-aim",
        source_ref: "frames 3, 4, 5",
        prerequisites: [],
        gate_ids: ["bayes-decision-check"],
        quiz_ids: [],
      },
      {
        id: "bayes-formula",
        title: "Bayes formula and conditional probability",
        lecture_id: "lecture-03",
        section_id: "bayes-formula",
        source_ref: "frames 6, 7, 8, 9",
        prerequisites: ["bayesian-decision-theory-the-aim"],
        gate_ids: [],
        quiz_ids: [],
      },
      {
        id: "losses-and-risks",
        title: "Losses, risks, and reject decisions",
        lecture_id: "lecture-03",
        section_id: "losses-and-risks",
        source_ref: "frames 33, 34, 35, 36, 37, 38",
        prerequisites: ["bayes-formula"],
        gate_ids: [],
        quiz_ids: ["losses-and-risks-quiz", "risk-threshold-check"],
      },
    ],
    gates: [
      {
        id: "bayes-decision-check",
        concept_id: "bayesian-decision-theory-the-aim",
        title: "Bayesian decision theory",
        prompt: "Demonstrate the learning outcome for Bayesian decision theory.",
        evidence_criteria: [
          {
            id: "posterior",
            description: "Connect posterior, evidence, and decision.",
            required: true,
          },
        ],
        transfer_prompt: "Apply the decision rule to a changed case.",
        review_after_days: 2,
        revision: "a".repeat(64),
        section_id: "bayesian-decision-theory-the-aim",
        source_ref: "frames 3, 4, 5",
      },
    ],
  };
}
