import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import type { LearningDesignReview } from "./learningDesignTypes";
import type { LoginSession } from "./types";
import { useProfessorLearningDesignReviews } from "./useProfessorLearningDesignReviews";
import { learningDesignReportFixture } from "./testLearningDesignReportFixture";

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
          report_revision: serverReview.report.report_revision,
          acknowledged_warning_ids: [],
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
      learning_map_revision: serverReview.learning_map.revision,
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

it.each(["resolve", "reject"] as const)(
  "ignores an old GET %s after switching courses with the same lecture ids",
  async (outcome) => {
    const oldGet = deferred<Response>();
    const newGet = deferred<Response>();
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => (url.includes("course-old") ? oldGet.promise : newGet.promise)),
    );
    const { result, rerender } = renderHook(
      ({ courseId }) =>
        useProfessorLearningDesignReviews({
          courseId,
          lectureIds: ["lecture-01"],
          revisionKey: "generation-1",
          session,
        }),
      { initialProps: { courseId: "course-old" } },
    );

    rerender({ courseId: "course-new" });
    await act(() =>
      outcome === "resolve"
        ? oldGet.resolve(response(review("a", "professor-demo")) as Response)
        : oldGet.reject(new Error("old load failed")),
    );
    expect(result.current.reviews).toEqual({});
    expect(result.current.allApproved).toBe(false);
    expect(result.current.error).toBeNull();

    await act(() => newGet.resolve(response(review("b", null)) as Response));
    await waitFor(() =>
      expect(result.current.reviews["lecture-01"].draft_digest).toBe("b".repeat(64)),
    );
    expect(result.current.allApproved).toBe(false);
  },
);

it.each([
  ["save", "resolve"],
  ["save", "reject"],
  ["approve", "resolve"],
  ["approve", "reject"],
] as const)("ignores an old %s %s after a revision switch", async (operation, outcome) => {
  const mutation = deferred<Response>();
  let getCount = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn((_url: string, init?: RequestInit) => {
      if (init?.method === "PUT" || init?.method === "POST") return mutation.promise;
      getCount += 1;
      return Promise.resolve(response(review(getCount === 1 ? "a" : "b", null)));
    }),
  );
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

  if (operation === "save") {
    void result.current.save("lecture-01", updateFor(result.current.reviews["lecture-01"]));
  } else {
    void result.current.approve("lecture-01");
  }
  rerender({ revisionKey: "generation-2" });
  await waitFor(() =>
    expect(result.current.reviews["lecture-01"].draft_digest).toBe("b".repeat(64)),
  );

  await act(() =>
    outcome === "resolve"
      ? mutation.resolve(response(review("a", "professor-demo")) as Response)
      : mutation.reject(new Error(`old ${operation} failed`)),
  );
  expect(result.current.reviews["lecture-01"].draft_digest).toBe("b".repeat(64));
  expect(result.current.allApproved).toBe(false);
  expect(result.current.error).toBeNull();
});

function review(digest: string, approvedBy: string | null): LearningDesignReview {
  return {
    schema_version: 2,
    course_id: "course-1",
    lecture_id: "lecture-01",
    draft_digest: digest.repeat(64),
    source_revision: "s".repeat(64),
    factual_quality_separate: true,
    report: learningDesignReportFixture({
      draftDigest: digest.repeat(64),
      sourceRevision: "s".repeat(64),
      learningMapRevision: "m".repeat(64),
    }),
    approval: approvedBy
      ? {
          approved_by: approvedBy,
          approved_at: "2026-08-09T12:00:00Z",
          draft_digest: digest.repeat(64),
          source_revision: "s".repeat(64),
          learning_map_revision: "m".repeat(64),
          report_revision: "r".repeat(64),
          acknowledged_warning_ids: [],
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

function updateFor(current: LearningDesignReview) {
  return {
    draft_digest: current.draft_digest,
    source_revision: current.source_revision,
    learning_map_revision: current.learning_map.revision,
    objective: current.learning_map.objective,
    gates: [],
    prerequisites: [],
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((onResolve, onReject) => {
    resolve = onResolve;
    reject = onReject;
  });
  return { promise, reject, resolve };
}

function response(payload: unknown) {
  return { ok: true, json: async () => payload };
}
