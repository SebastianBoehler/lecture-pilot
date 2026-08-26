import { expect, it, vi } from "vitest";

import { requireCurrentPracticeApprovals } from "./practiceDesignGate";
import type { LoginSession } from "./types";

const session = {
  account_type: "professor",
  courses: [],
  roles: ["professor"],
  term: "Summer 2026",
  username: "professor-demo",
} as LoginSession;

it("uses authoritative lecture readiness instead of comparing with the course routing digest", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string | URL | Request) => {
      const url = String(input);
      const payload = url.endsWith("/readiness")
        ? {
            lecture_id: "lecture-01",
            current_source_revision: "b".repeat(64),
            practice_design_revision: "d".repeat(64),
            ready_for_generation: true,
          }
        : design("b");
      return Promise.resolve(
        new Response(JSON.stringify(payload), {
          headers: { "Content-Type": "application/json" },
        }),
      );
    }),
  );

  await expect(
    requireCurrentPracticeApprovals({
      courseId: "course-1",
      lectureIds: ["lecture-01"],
      session,
    }),
  ).resolves.toBeUndefined();
});

function design(revision: string) {
  return {
    schema_version: 1,
    course_id: "course-1",
    lecture_id: "lecture-01",
    lecture_title: "Lecture 01",
    objective: "Apply the rule.",
    source_revision: revision.repeat(64),
    revision: "d".repeat(64),
    approval: {
      approved_by: "professor-demo",
      approved_at: "2026-08-26T12:00:00Z",
      source_revision: revision.repeat(64),
      practice_design_revision: "d".repeat(64),
    },
    targets: [],
  };
}
