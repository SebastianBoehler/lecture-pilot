import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import type { PracticeDesign } from "./practiceDesignTypes";
import type { LoginSession } from "./types";
import { useProfessorPracticeDesigns } from "./useProfessorPracticeDesigns";

const session = {
  account_type: "professor",
  courses: [],
  roles: ["professor"],
  term: "Summer 2026",
  username: "professor-demo",
} as LoginSession;

afterEach(() => vi.unstubAllGlobals());

it("loads every lecture independently and records a 404 as absent", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) =>
      Promise.resolve(
        url.includes("lecture-01")
          ? response(design("lecture-01"))
          : response({ detail: "Practice design has not been proposed." }, 404),
      ),
    ),
  );
  const { result } = renderHook(() =>
    useProfessorPracticeDesigns({ courseId: "course-1", session }),
  );

  await act(() => result.current.loadAll(["lecture-01", "lecture-02"]));

  expect(result.current.designs).toEqual({ "lecture-01": design("lecture-01") });
  expect(result.current.error).toBeNull();
  expect(result.current.allApproved(["lecture-01", "lecture-02"])).toBe(false);
  expect(result.current.allApproved([])).toBe(false);
});

it("replaces only the saved lecture and reflects approval clearing", async () => {
  let saved = false;
  vi.stubGlobal(
    "fetch",
    vi.fn((_url: string, init?: RequestInit) => {
      if (init?.method === "PUT") {
        saved = true;
        return Promise.resolve(response(design("lecture-01", null, "e")));
      }
      return Promise.resolve(response(design("lecture-01", "professor-demo")));
    }),
  );
  const { result } = renderHook(() =>
    useProfessorPracticeDesigns({ courseId: "course-1", session }),
  );
  await act(() => result.current.loadAll(["lecture-01"]));

  await act(() => result.current.save("lecture-01", update(result.current.designs["lecture-01"])));

  expect(saved).toBe(true);
  expect(result.current.designs["lecture-01"].revision).toBe("e".repeat(64));
  expect(result.current.designs["lecture-01"].approval).toBeNull();
  expect(result.current.allApproved(["lecture-01"])).toBe(false);
});

it("requires approval revisions to match the current design", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(response(design("lecture-01", "professor-demo")))),
  );
  const { result } = renderHook(() =>
    useProfessorPracticeDesigns({ courseId: "course-1", session }),
  );
  await act(() => result.current.loadAll(["lecture-01"]));

  expect(result.current.allApproved(["lecture-01"])).toBe(true);
  const mismatched = {
    ...result.current.designs["lecture-01"],
    approval: {
      ...result.current.designs["lecture-01"].approval!,
      practice_design_revision: "x".repeat(64),
    },
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(response(mismatched))),
  );
  await act(() => result.current.loadAll(["lecture-01"]));

  expect(result.current.allApproved(["lecture-01"])).toBe(false);
});

it("keeps a stale approval conflict visible and reset removes changed lectures", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((_url: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        return Promise.resolve(
          response({ detail: "The practice design or source revision changed. Reload it." }, 409),
        );
      }
      return Promise.resolve(response(design("lecture-01")));
    }),
  );
  const { result } = renderHook(() =>
    useProfessorPracticeDesigns({ courseId: "course-1", session }),
  );
  await act(() => result.current.loadAll(["lecture-01"]));

  await act(() => result.current.approve("lecture-01"));
  expect(result.current.error).toBe("The practice design or source revision changed. Reload it.");

  act(() => result.current.reset(["lecture-01"]));
  expect(result.current.designs).toEqual({});
  expect(result.current.error).toBeNull();
});

it("does not let an older lecture request overwrite a newer lecture state", async () => {
  const first = deferred<Response>();
  const second = deferred<Response>();
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => (url.includes("lecture-01") ? first.promise : second.promise)),
  );
  const { result } = renderHook(() =>
    useProfessorPracticeDesigns({ courseId: "course-1", session }),
  );

  void result.current.loadAll(["lecture-01"]);
  void result.current.loadAll(["lecture-02"]);
  await waitFor(() => expect(result.current.pendingLectureId).toBe("lecture-02"));
  await act(() => second.resolve(response(design("lecture-02"))));
  await waitFor(() => expect(result.current.pendingLectureId).toBe("lecture-01"));
  await waitFor(() => expect(result.current.designs["lecture-02"]).toBeDefined());
  await act(() => first.resolve(response(design("lecture-01"))));

  expect(result.current.designs).toEqual({
    "lecture-01": design("lecture-01"),
    "lecture-02": design("lecture-02"),
  });
});

function design(
  lectureId: string,
  approvedBy: string | null = null,
  revision = "d",
): PracticeDesign {
  return {
    schema_version: 1,
    course_id: "course-1",
    lecture_id: lectureId,
    lecture_title: "Bayes rule",
    objective: "Calculate a posterior from evidence.",
    source_revision: "s".repeat(64),
    revision: revision.repeat(64),
    approval: approvedBy
      ? {
          approved_by: approvedBy,
          approved_at: "2026-08-26T12:00:00Z",
          source_revision: "s".repeat(64),
          practice_design_revision: revision.repeat(64),
        }
      : null,
    targets: [
      {
        id: "posterior",
        title: "Posterior",
        outcome: "Calculate a posterior from evidence.",
        baseline_task: "Calculate the posterior.",
        independent_exit_task: "Calculate another posterior.",
        delayed_transfer_task: "Calculate a diagnostic posterior.",
        evidence_criteria: [
          { id: "substitute", description: "Uses stated values.", required: true },
        ],
        misconceptions: [],
        hint_ladder: [],
        review_after_days: 7,
        source_refs: ["Lecture01.md"],
      },
    ],
  };
}

function update(current: PracticeDesign) {
  return {
    source_revision: current.source_revision,
    practice_design_revision: current.revision,
    lecture_title: current.lecture_title,
    objective: current.objective,
    targets: current.targets,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((onResolve) => {
    resolve = onResolve;
  });
  return { promise, resolve };
}

function response(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
