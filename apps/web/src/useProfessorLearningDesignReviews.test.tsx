import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import type { LearningDesignReview } from "./learningDesignTypes";
import type { LoginSession } from "./types";
import { useProfessorLearningDesignReviews } from "./useProfessorLearningDesignReviews";

const session = {
  account_type: "professor",
  courses: [],
  roles: ["professor"],
  term: "Sommer 2026",
  username: "professor-demo",
} as LoginSession;

afterEach(() => vi.unstubAllGlobals());

it("loads, edits, approves, and refreshes draft-bound reviews per lecture", async () => {
  let serverReview = review("d", null);
  const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
    if (init?.method === "PUT") {
      const body = JSON.parse(String(init.body));
      serverReview = {
        ...serverReview,
        learning_map: { ...serverReview.learning_map, objective: body.objective },
        approval: null,
      };
    }
    if (init?.method === "POST") {
      serverReview = {
        ...serverReview,
        approval: {
          approved_by: "professor-demo",
          approved_at: "2026-08-09T12:00:00Z",
          draft_digest: serverReview.draft_digest,
          source_revision: serverReview.source_revision,
          learning_map_revision: serverReview.learning_map.revision,
        },
      };
    }
    return response(serverReview);
  });
  vi.stubGlobal("fetch", fetchMock);
  const { result, rerender } = renderHook(
    ({ revisionKey }) =>
      useProfessorLearningDesignReviews({
        courseId: "course-1",
        lectureIds: ["lecture-01"],
        revisionKey,
        session,
      }),
    { initialProps: { revisionKey: "generation-1" } },
  );

  await waitFor(() => expect(result.current.reviews["lecture-01"]).toBeDefined());
  expect(result.current.allApproved).toBe(false);
  await act(() =>
    result.current.save("lecture-01", {
      draft_digest: serverReview.draft_digest,
      source_revision: serverReview.source_revision,
      objective: "Edited objective",
      gates: [],
      prerequisites: [],
    }),
  );
  expect(result.current.reviews["lecture-01"].learning_map.objective).toBe("Edited objective");
  await act(() => result.current.approve("lecture-01"));
  expect(result.current.allApproved).toBe(true);

  serverReview = review("e", null);
  rerender({ revisionKey: "generation-2" });
  await waitFor(() =>
    expect(result.current.reviews["lecture-01"].draft_digest).toBe("e".repeat(64)),
  );
  expect(result.current.allApproved).toBe(false);
});

function review(digest: string, approvedBy: string | null): LearningDesignReview {
  return {
    schema_version: 1,
    course_id: "course-1",
    lecture_id: "lecture-01",
    draft_digest: digest.repeat(64),
    source_revision: "s".repeat(64),
    factual_quality_separate: true,
    warnings: [],
    approval: approvedBy
      ? {
          approved_by: approvedBy,
          approved_at: "2026-08-09T12:00:00Z",
          draft_digest: digest.repeat(64),
          source_revision: "s".repeat(64),
          learning_map_revision: "m".repeat(64),
        }
      : null,
    learning_map: {
      course_id: "course-1",
      lecture_id: "lecture-01",
      title: "Lecture",
      objective: "Initial objective",
      revision: "m".repeat(64),
      nodes: [],
      gates: [],
    },
  };
}

function response(payload: unknown) {
  return { ok: true, json: async () => payload };
}
