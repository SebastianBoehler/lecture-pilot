import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import type { PracticeDesign } from "./practiceDesignTypes";
import { practiceDesignFixture } from "./practiceDesignTestFixtures";
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
    vi.fn((url: string) => {
      const current = design("lecture-01");
      return Promise.resolve(
        url.includes("lecture-01")
          ? resourceResponse(url, current)
          : response({ detail: "Practice design has not been proposed." }, 404),
      );
    }),
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
    vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "PUT") {
        saved = true;
        return Promise.resolve(response(design("lecture-01", null, "e")));
      }
      return Promise.resolve(resourceResponse(url, design("lecture-01", "professor-demo")));
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

it("requests a revision-bound semantic review and stores the reviewed design", async () => {
  const requests: string[] = [];
  const reviewed = deferred<Response>();
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, init?: RequestInit) => {
      requests.push(`${init?.method ?? "GET"} ${url}`);
      const current = design("lecture-01");
      if (url.endsWith("/review")) return reviewed.promise;
      return Promise.resolve(resourceResponse(url, current));
    }),
  );
  const { result } = renderHook(() =>
    useProfessorPracticeDesigns({ courseId: "course-1", session }),
  );
  await act(() => result.current.loadAll(["lecture-01"]));

  let review: Promise<void>;
  act(() => {
    review = result.current.review("lecture-01");
  });
  await waitFor(() => expect(result.current.pendingAction).toBe("review"));
  const current = design("lecture-01");
  await act(() =>
    reviewed.resolve(
      response({
        ...current,
        quality_review: {
          source_revision: current.source_revision,
          practice_design_revision: current.revision,
          checks: [],
        },
      }),
    ),
  );
  await act(() => review!);

  expect(requests).toContainEqual(expect.stringMatching(/^POST .*\/practice-design\/review$/));
  expect(result.current.pendingAction).toBeNull();
  expect(result.current.designs["lecture-01"].quality_review?.practice_design_revision).toBe(
    "d".repeat(64),
  );
});

it("requires approval revisions to match the current design", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) =>
      Promise.resolve(resourceResponse(url, design("lecture-01", "professor-demo"))),
    ),
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
    vi.fn((url: string) => Promise.resolve(resourceResponse(url, mismatched))),
  );
  await act(() => result.current.loadAll(["lecture-01"]));

  expect(result.current.allApproved(["lecture-01"])).toBe(false);
});

it("reloads a stale approval conflict and posts the refreshed revision on retry", async () => {
  const approvalRevisions: string[] = [];
  let approvalAttempts = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn((_url: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        approvalAttempts += 1;
        approvalRevisions.push(JSON.parse(String(init.body)).practice_design_revision);
        return Promise.resolve(
          approvalAttempts === 1
            ? response(
                { detail: "The practice design or source revision changed. Reload it." },
                409,
              )
            : response(design("lecture-01", "professor-demo", "e")),
        );
      }
      return Promise.resolve(
        response(approvalAttempts === 0 ? design("lecture-01") : design("lecture-01", null, "e")),
      );
    }),
  );
  const { result } = renderHook(() =>
    useProfessorPracticeDesigns({ courseId: "course-1", session }),
  );
  await act(() => result.current.loadAll(["lecture-01"]));

  await act(() => result.current.approve("lecture-01"));
  expect(result.current.error).toBe("The practice design or source revision changed. Reload it.");
  expect(result.current.designs["lecture-01"].revision).toBe("e".repeat(64));

  await act(() => result.current.approve("lecture-01"));
  expect(approvalRevisions).toEqual(["d".repeat(64), "e".repeat(64)]);
  expect(result.current.designs["lecture-01"].approval?.practice_design_revision).toBe(
    "e".repeat(64),
  );
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

it("does not restore an unseen in-flight lecture after a full reset", async () => {
  const request = deferred<Response>();
  vi.stubGlobal(
    "fetch",
    vi.fn(() => request.promise),
  );
  const { result } = renderHook(() =>
    useProfessorPracticeDesigns({ courseId: "course-1", session }),
  );

  void result.current.loadAll(["lecture-01"]);
  await waitFor(() => expect(result.current.pendingLectureId).toBe("lecture-01"));
  act(() => result.current.reset());
  expect(result.current.pendingLectureId).toBeNull();

  await act(() => request.resolve(response(design("lecture-01"))));
  expect(result.current.designs).toEqual({});
});

it("ignores an in-flight completion after unmount", async () => {
  const request = deferred<Response>();
  vi.stubGlobal(
    "fetch",
    vi.fn(() => request.promise),
  );
  const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
  const { result, unmount } = renderHook(() =>
    useProfessorPracticeDesigns({ courseId: "course-1", session }),
  );

  void result.current.loadAll(["lecture-01"]);
  await waitFor(() => expect(result.current.pendingLectureId).toBe("lecture-01"));
  unmount();
  await act(() => request.resolve(response(design("lecture-01"))));

  expect(consoleError).not.toHaveBeenCalled();
  consoleError.mockRestore();
});

function design(
  lectureId: string,
  approvedBy: string | null = null,
  revision = "d",
): PracticeDesign {
  return practiceDesignFixture({
    approvedBy,
    lectureId,
    revision: revision.repeat(64),
    reviewSeverity: null,
    sourcePath: "Lecture01.md",
  });
}

function update(current: PracticeDesign) {
  return {
    source_revision: current.source_revision,
    practice_design_revision: current.revision,
    lecture_title: current.lecture_title,
    objective: current.objective,
    planning_context: current.planning_context,
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

function resourceResponse(url: string, current: PracticeDesign) {
  if (!url.endsWith("/readiness")) return response(current);
  const approval = current.approval;
  return response({
    lecture_id: current.lecture_id,
    current_source_revision: current.source_revision,
    practice_design_revision: current.revision,
    ready_for_generation: Boolean(
      approval &&
      approval.source_revision === current.source_revision &&
      approval.practice_design_revision === current.revision,
    ),
  });
}
