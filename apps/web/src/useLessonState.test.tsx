import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { LoginSession } from "./types";
import { useLessonState } from "./useLessonState";

afterEach(() => vi.unstubAllGlobals());

describe("useLessonState", () => {
  it("does not request learner state for a draft preview", () => {
    const fetchMock = vi.fn();
    const session = learner("professor-a");
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() =>
      useLessonState({
        courseId: "course-a",
        lectureId: "lecture-a",
        session,
        mode: "draft",
        enabled: true,
      }),
    );

    expect(fetchMock).not.toHaveBeenCalled();
    expect(result.current.state).toBeNull();
  });

  it("clears prior learner data while a different session hydrates", async () => {
    let resolveSecond: ((response: Response) => void) | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn((_, init?: RequestInit) => {
        const user = new Headers(init?.headers).get("X-User-Id");
        if (user === "student-b") {
          return new Promise<Response>((resolve) => {
            resolveSecond = resolve;
          });
        }
        return Promise.resolve(response("Private goal for A"));
      }),
    );
    const { result, rerender } = renderHook(
      ({ session }) =>
        useLessonState({
          courseId: "course-a",
          lectureId: "lecture-a",
          session,
          mode: "learner",
          enabled: true,
        }),
      { initialProps: { session: learner("student-a") } },
    );

    await waitFor(() =>
      expect(result.current.state?.active_session_goal).toBe("Private goal for A"),
    );
    rerender({ session: learner("student-b") });

    await waitFor(() => expect(result.current.loading).toBe(true));
    expect(result.current.state).toBeNull();
    await act(async () => resolveSecond?.(response(null)));
  });
});

function learner(username: string): LoginSession {
  return { username, term: "2026", courses: [] };
}

function response(goal: string | null) {
  return new Response(
    JSON.stringify({
      course_id: "course-a",
      lecture_id: "lecture-a",
      gate_statuses: {},
      quiz_states: {},
      active_session_goal: goal,
      pending_check: null,
      due_gate_reviews: [],
    }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
}
