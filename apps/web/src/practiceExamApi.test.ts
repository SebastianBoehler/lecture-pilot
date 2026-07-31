import { describe, expect, it, vi } from "vitest";

import { downloadPracticeExamPdf, generatePracticeExam } from "./practiceExamApi";
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

function json(payload: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}
