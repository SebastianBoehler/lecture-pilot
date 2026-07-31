import { describe, expect, it, vi } from "vitest";

import {
  downloadPracticeExamPdf,
  downloadPracticeExamSolutionPdf,
  generatePracticeExam,
  loadPracticeExamSolutions,
} from "./practiceExamApi";
import type { LoginSession } from "./types";

describe("practice exam API", () => {
  it("sends typed generation input with an idempotency key", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      json(examPayload()),
    );
    vi.stubGlobal("fetch", fetchMock);

    await generatePracticeExam(
      "course-1",
      { question_count: 25, duration_minutes: 90, ppi_source_ids: ["ppi-42"] },
      "practice-exam-request-0001",
      session,
    );

    const [, init] = fetchMock.mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(headers.get("Idempotency-Key")).toBe("practice-exam-request-0001");
    expect(headers.get("Authorization")).toBe("Bearer test-token");
    expect(JSON.parse(String(init?.body))).toEqual({
      question_count: 25,
      duration_minutes: 90,
      ppi_source_ids: ["ppi-42"],
    });
  });

  it("downloads an authenticated PDF blob", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(new Blob(["%PDF-test"], { type: "application/pdf" }), {
          status: 200,
          headers: { "Content-Type": "application/pdf" },
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await downloadPracticeExamPdf("course-1", "a".repeat(32), session);

    expect(result.type).toBe("application/pdf");
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get("Authorization")).toBe(
      "Bearer test-token",
    );
  });

  it("loads a separate authenticated solution sheet", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      json(solutionPayload()),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadPracticeExamSolutions("course-1", "a".repeat(32), session);

    expect(result.questions[0].answer_index).toBe(0);
    expect(String(fetchMock.mock.calls[0][0])).toContain("/solutions");
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get("Authorization")).toBe(
      "Bearer test-token",
    );
  });

  it("downloads the separate authenticated solution PDF", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(new Blob(["%PDF-solutions"], { type: "application/pdf" }), {
          status: 200,
          headers: { "Content-Type": "application/pdf" },
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await downloadPracticeExamSolutionPdf("course-1", "a".repeat(32), session);

    expect(result.type).toBe("application/pdf");
    expect(String(fetchMock.mock.calls[0][0])).toContain("/solutions/pdf");
  });
});

const session: LoginSession = {
  username: "student-a",
  term: "Summer 2026",
  roles: ["student"],
  courses: [],
  access_token: "test-token",
};

function examPayload() {
  return {
    id: "a".repeat(32),
    course_id: "course-1",
    title: "Practice exam",
    language: "en",
    instructions: ["Answer all questions."],
    duration_minutes: 90,
    created_at: "2026-07-31T10:00:00Z",
    total_points: 40,
    questions: [],
  };
}

function solutionPayload() {
  return {
    exam_id: "a".repeat(32),
    title: "Practice exam solutions",
    total_points: 40,
    questions: [
      {
        id: "q-01",
        kind: "multiple_choice",
        points: 3,
        answer_index: 0,
        reference_answer: null,
        rubric: [],
      },
    ],
  };
}

function json(payload: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}
