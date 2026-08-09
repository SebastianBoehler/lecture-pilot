import { vi } from "vitest";

import { canvasPayload } from "./testCanvasFixture";
import { learningMapPayload } from "./testLearningMapFixture";
import { quizAttemptResponse } from "./testQuizAttemptFixture";

export function mockLoginFetch({ published = false }: { published?: boolean } = {}) {
  return vi.fn(async (url: string, init?: RequestInit) => {
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
    if (url.includes("/analytics/quiz-answer")) return json(quizAttemptResponse(init));
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
    if (url.includes("/analytics/quiz-answer")) return json(quizAttemptResponse(_init));

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
