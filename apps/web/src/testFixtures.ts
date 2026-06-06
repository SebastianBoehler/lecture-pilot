import { vi } from "vitest";

export function mockLoginFetch() {
  return vi.fn(async (url: string, _init?: RequestInit) => {
    if (url.endsWith("/auth/login")) {
      return {
        ok: true,
        json: async () => loginPayload(),
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
}: {
  tutorResponse?: Record<string, unknown>;
} = {}) {
  return vi.fn(async (url: string, _init?: RequestInit) => {
    if (url.endsWith("/auth/login")) {
      return {
        ok: true,
        json: async () => loginPayload(),
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
          model: "openrouter/z-ai/glm-5.1",
          created_at: "2026-06-05T20:00:00Z",
        },
    };
  });
}

export function soccerCanvasSection() {
  return {
    id: "student-soccer-bayes-example",
    title: "Soccer scouting example",
    source_ref: "student workspace",
    blocks: [
      {
        id: "student-soccer-bayes-example-p-1",
        type: "paragraph",
        text: "A scouting report is evidence that updates the posterior belief about a player fit.",
        items: [],
      },
      {
        id: "student-soccer-bayes-example-list",
        type: "list",
        items: ["Prior player fit", "Likelihood of report", "Decision risk of signing"],
      },
    ],
  };
}

function loginPayload() {
  return {
    username: "student01",
    email: null,
    term: "Sommer 2026",
    courses: [
      {
        id: "alma-machine-learning",
        title: "Machine Learning",
        professor: "Department of Computer Science",
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
      ".lecturepilot/workspaces/students/hash/courses/martius-ml/lectures/lecture-03/canvas.json",
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
            id: "bayes-formula-list",
            type: "list",
            items: ["Prior", "Likelihood", "Evidence", "Posterior"],
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
        ],
      },
    ],
  };
}
