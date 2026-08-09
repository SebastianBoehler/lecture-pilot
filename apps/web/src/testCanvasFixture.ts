export function canvasPayload() {
  return {
    id: "martius-ml-lecture-03",
    course_id: "martius-ml",
    lecture_id: "lecture-03",
    title: "Bayesian Decision Theory",
    source_kind: "latex",
    source_ref: "Lecture03-eng.tex",
    workspace_path:
      ".lecturepilot/workspaces/students/hash/courses/martius-ml/lectures/lecture-03/canvas/index.md",
    sections: [
      {
        id: "bayesian-decision-theory-the-aim",
        title: "Decision making under uncertainty",
        source_ref: "frames 3, 4, 5",
        blocks: [
          {
            id: "bayesian-decision-theory-the-aim-asset-1",
            type: "asset",
            items: [],
            asset_path: "Ch3/spam-DALL-E.jpg",
            asset_url: "/course-assets/martius-ml/lecture-03/Ch3/spam-DALL-E.jpg",
            caption: "Ch3/spam-DALL-E.jpg",
          },
          {
            id: "bayesian-decision-theory-the-aim-p-1",
            type: "paragraph",
            text: "Bayesian decision theory connects probabilities, observations, and decisions.",
            items: [],
          },
        ],
      },
      {
        id: "bayes-formula",
        title: "Bayes formula and conditional probability",
        source_ref: "frames 6, 7, 8, 9",
        blocks: [
          {
            id: "bayes-formula-asset-1",
            type: "asset",
            items: [],
            asset_path: "Ch3/Venn_C-X_1.pdf",
            asset_url: "/course-assets/martius-ml/lecture-03/Ch3/Venn_C-X_1.pdf",
            caption: "Ch3/Venn_C-X_1.pdf",
          },
          {
            id: "bayes-formula-list",
            type: "list",
            items: ["Prior", "Likelihood", "Evidence", "Posterior", "P(heads) = $\\nicefrac 12$"],
          },
          {
            id: "bayes-formula-math-1",
            type: "math",
            text: "P(C\\mid X) = \\frac{P(X\\mid C)P(C)}{P(X)}",
            items: [],
          },
          {
            id: "bayes-formula-p-1",
            type: "paragraph",
            text: "Bayes formula turns evidence $X$ into a posterior distribution $P(C\\mid X)$.",
            items: [],
          },
        ],
      },
      {
        id: "bayes-rule-to-sum-up",
        title: "Bayes rule for classification",
        source_ref: "frames 10, 11, 12, 13, 14, 15, 16, 17",
        blocks: [
          {
            id: "bayes-rule-to-sum-up-p-1",
            type: "paragraph",
            text: "The rule combines prior, likelihood, and evidence for classification.",
            items: [],
          },
        ],
      },
      {
        id: "naive-bayes-classifiers",
        title: "Naive Bayes spam filter",
        source_ref: "frames 21, 22, 23, 24, 25, 26, 27, 28",
        blocks: [
          {
            id: "naive-bayes-classifiers-p-1",
            type: "paragraph",
            text: "Naive Bayes simplifies the likelihood by assuming feature independence.",
            items: [],
          },
        ],
      },
      {
        id: "professor-selected-videos",
        title: "Professor selected videos",
        source_ref: "course media workspace",
        blocks: [
          {
            id: "youtube-abc123abc12",
            type: "video",
            text: "ML Course · 12:30",
            items: [],
            asset_url: "https://www.youtube.com/watch?v=abc123abc12",
            caption: "Bayesian decision theory walkthrough",
          },
        ],
      },
      {
        id: "losses-and-risks",
        title: "Losses, risks, and reject decisions",
        source_ref: "frames 33, 34, 35, 36, 37, 38",
        blocks: [
          {
            id: "losses-and-risks-p-1",
            type: "paragraph",
            text: "Expected risk changes the best action when mistakes have different costs.",
            items: [],
          },
          {
            id: "losses-and-risks-p-2",
            type: "paragraph",
            text: "The learner should compare posterior probabilities with loss values.",
            items: [],
          },
          {
            id: "losses-and-risks-p-3",
            type: "paragraph",
            text: "Reject decisions are useful when every class assignment is too risky.",
            items: [],
          },
          {
            id: "losses-and-risks-math-1",
            type: "math",
            text: "R(\\alpha_i\\mid x) = \\sum_k \\lambda_{ik}P(C_k\\mid x)",
            items: [],
          },
          {
            id: "losses-and-risks-math-2",
            type: "math",
            text: "R(\\alpha_{K+1}\\mid x) = \\lambda",
            items: [],
          },
          {
            id: "losses-and-risks-math-3",
            type: "math",
            text: "\\text{choose reject if } R(\\alpha_{K+1}\\mid x) < R(\\alpha_i\\mid x)",
            items: [],
          },
          {
            id: "losses-and-risks-quiz",
            type: "quiz",
            caption: "Retrieval check",
            text: "Which quantity should be minimized when mistakes have different costs?",
            items: ["Posterior probability alone", "Expected risk", "Raw evidence count"],
            answer_index: 1,
          },
          {
            id: "risk-threshold-check",
            type: "component",
            component_id: "risk-threshold-check",
            component_type: "single_choice_quiz",
            component_ref: "risk-threshold-check.yaml",
            component_version: 2,
            caption: "Risk threshold component",
            text: "What changes when false negatives are much more costly?",
            items: ["The loss-sensitive threshold", "The class label names"],
            option_ids: ["loss-threshold", "class-label-names"],
            answer_index: 0,
          },
        ],
      },
    ],
  };
}
