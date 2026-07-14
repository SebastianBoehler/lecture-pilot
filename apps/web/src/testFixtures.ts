import { vi } from "vitest";

import { learningMapPayload } from "./testLearningMapFixture";

export function mockLoginFetch({ published = false }: { published?: boolean } = {}) {
  return vi.fn(async (url: string, _init?: RequestInit) => {
    if (url.endsWith("/auth/login")) {
      return {
        ok: true,
        json: async () => loginPayload(),
      };
    }
    if (url.includes("/canvas/publication")) {
      return {
        ok: true,
        json: async () => publicationPayload(url, published),
      };
    }
    if (url.endsWith("/courses")) return json(courseListPayload());
    if (/\/courses\/[^/]+\/lectures$/.test(url)) return json(lectureListPayload(published));
    if (url.includes("/learning-map")) {
      return {
        ok: true,
        json: async () => learningMapPayload(),
      };
    }
    return {
      ok: true,
      json: async () => canvasPayload(),
    };
  });
}

export function mockLoginAndTutorFetch({
  tutorResponse,
  published = true,
}: {
  tutorResponse?: Record<string, unknown>;
  published?: boolean;
} = {}) {
  return vi.fn(async (url: string, _init?: RequestInit) => {
    if (url.endsWith("/auth/login")) {
      return {
        ok: true,
        json: async () => loginPayload(),
      };
    }

    if (url.includes("/canvas/publication")) {
      return {
        ok: true,
        json: async () => publicationPayload(url, published),
      };
    }

    if (url.endsWith("/courses")) return json(courseListPayload());
    if (/\/courses\/[^/]+\/lectures$/.test(url)) return json(lectureListPayload(published));

    if (url.includes("/learning-map")) {
      return {
        ok: true,
        json: async () => learningMapPayload(),
      };
    }

    if (url.includes("/canvas")) {
      return {
        ok: true,
        json: async () => canvasPayload(),
      };
    }

    return {
      ok: true,
      json: async () =>
        tutorResponse ?? {
          message: "Bayes answer from the tutor.",
          canvas_commands: [{ type: "focus_section", section_id: "bayes-formula" }],
          quality_gate: {
            gate_id: "bayes-decision-check",
            status: "needs_evidence",
            reason: "Student has not answered the concrete gate yet.",
            next_prompt: "State how posterior, likelihood, and risk connect.",
          },
          artifacts: [],
          model: "gemini/gemini-3.1-flash-lite",
          created_at: "2026-06-05T20:00:00Z",
        },
    };
  });
}

function courseListPayload() {
  return [
    {
      access_policy: "public",
      id: "martius-ml",
      title: "Grundlagen des Maschinellen Lernens",
      professor: "Prof. Georg Martius",
      term: "Sommer 2026",
    },
  ];
}

function lectureListPayload(published: boolean) {
  if (!published) return [];
  return [
    ["lecture-01", "Introduction and Learning Setup", "2026-05-06", "present", "Lecture01-eng.tex"],
    [
      "lecture-02",
      "Linear Models and Generalization",
      "2026-05-13",
      "unknown",
      "Lecture02-eng.tex",
    ],
    ["lecture-03", "Bayesian Decision Theory", "2026-06-04", "absent", "Lecture03-eng.tex"],
  ].map(([id, title, date, attendance, material_path]) => ({
    lecture: { id, title, date, material_path },
    attendance,
    content_ready: true,
    effective_publication_at: `${date}T00:00:00+02:00`,
    release_status: "released",
    unlocked: true,
  }));
}

function json(payload: unknown) {
  return { ok: true, json: async () => payload };
}

function publicationPayload(url: string, published: boolean) {
  const lectureId = url.match(/lectures\/([^/]+)\/canvas\/publication/)?.[1] ?? "lecture-03";
  return {
    course_id: "martius-ml",
    lecture_id: lectureId,
    published,
    version: published ? 1 : null,
    published_at: published ? "2026-06-12T10:00:00Z" : null,
  };
}

function loginPayload() {
  return {
    username: "student01",
    display_name: "Student Example",
    email: "student01@uni-tuebingen.de",
    term: "Sommer 2026",
    tenant_id: "tenant-tuebingen",
    roles: ["student"],
    access_token: "signed-test-token",
    courses: [
      {
        id: "alma-ml4202-probabilistic-machine-learning",
        title: "ML4202 Probabilistic Machine Learning (Probabilistic Inference and Learning)",
        professor: "Fachbereich Informatik, Methoden des Maschinellen Lernens",
        term: "Sommer 2026",
      },
      {
        id: "alma-info4193-natural-language-processing",
        title: "INFO4193 Natural Language Processing",
        professor: "Fachbereich Informatik",
        term: "Sommer 2026",
      },
    ],
  };
}

function canvasPayload() {
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
