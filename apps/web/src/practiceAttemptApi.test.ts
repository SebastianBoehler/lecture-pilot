import { expect, it, vi } from "vitest";
import { listPracticeAttempts, savePracticeAttempt } from "./practiceAttemptApi";
import type { LoginSession } from "./types";

const session: LoginSession = {
  username: "student",
  term: "",
  roles: ["student"],
  courses: [],
  access_token: "private-token",
};

it("sends the authenticated snapshot and preserves the retry identifier", async () => {
  const fetcher = vi.fn(
    async () => new Response(JSON.stringify({ id: "attempt" }), { status: 200 }),
  );
  vi.stubGlobal("fetch", fetcher);
  const submission = { id: "attempt", answers: { q: { text: "My answer" } } };
  await savePracticeAttempt("course", "exam", session, submission);
  const [url, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
  expect(url).toContain("/courses/course/practice-exams/exam/attempts");
  expect(new Headers(init.headers).get("Authorization")).toBe("Bearer private-token");
  expect(JSON.parse(String(init.body))).toEqual(submission);
  expect(init.credentials).toBe("include");
});

it("surfaces server errors without reporting an empty history", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(JSON.stringify({ detail: "Student access is required." }), { status: 403 }),
    ),
  );
  await expect(listPracticeAttempts("course", "exam", session)).rejects.toThrow(
    "Student access is required.",
  );
});
