import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { PracticeExamPanel } from "./PracticeExamPanel";
import { renderWithI18n } from "./test/renderWithI18n";
import type { LoginSession, UniversityCourse } from "./types";

it("uses a fresh idempotency key when the learner retries a failed generation", async () => {
  const keys: string[] = [];
  let attempts = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (!String(input).endsWith("/practice-exam-generations")) return json([]);
      keys.push(new Headers(init?.headers).get("Idempotency-Key") ?? "");
      attempts += 1;
      return attempts === 1
        ? json({ detail: "Practice exam generation failed validation. Please retry." }, 502)
        : json(exam);
    }),
  );
  const user = userEvent.setup();
  renderWithI18n(<PracticeExamPanel course={course} session={session} />);

  await user.click(await screen.findByRole("button", { name: "Generate exam" }));
  await user.click(screen.getByRole("button", { name: "Generate 25-question exam" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("failed validation");
  await user.click(screen.getByRole("button", { name: "Generate 25-question exam" }));
  expect(await screen.findByRole("dialog", { name: "Practice exam" })).toBeInTheDocument();
  expect(keys).toHaveLength(2);
  expect(keys[1]).not.toBe(keys[0]);
});

const session: LoginSession = {
  username: "student-a",
  term: "Summer 2026",
  roles: ["student"],
  courses: [],
  access_token: "test-token",
};
const course: UniversityCourse = {
  id: "course-1",
  title: "Machine Learning",
  professor: "Professor Example",
  term: "Summer 2026",
};
const exam = {
  id: "a".repeat(32),
  course_id: "course-1",
  title: "Practice exam",
  language: "en",
  instructions: ["Answer every question."],
  duration_minutes: 90,
  created_at: "2026-07-31T10:00:00Z",
  total_points: 2,
  questions: [{ id: "q-01", kind: "open_ended", prompt: "Explain risk.", points: 2, options: [] }],
};

function json(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
