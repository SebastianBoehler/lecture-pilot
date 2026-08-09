import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { LearnerLessonState } from "./learnerLessonStateTypes";
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

  it.each([
    ["failure", "needs_evidence", pendingCheck("repair-check")],
    ["completion", "passed", null],
  ] as const)(
    "rehydrates server-owned state after delayed-review %s",
    async (_, status, pending) => {
      let state = lessonState("Before", {
        pending_check: pendingCheck("old-check"),
        due_gate_reviews: [dueReview("old-check")],
      });
      vi.stubGlobal(
        "fetch",
        vi.fn(() => Promise.resolve(stateResponse(state))),
      );
      const session = learner("student-a");
      const { result } = renderHook(() =>
        useLessonState({
          courseId: "course-a",
          lectureId: "lecture-a",
          session,
          mode: "learner",
          enabled: true,
        }),
      );
      await waitFor(() => expect(result.current.state?.active_session_goal).toBe("Before"));
      state = lessonState("After", {
        gate_statuses: { "old-check": status },
        pending_check: pending,
        due_gate_reviews: [],
      });

      await act(async () => {
        await result.current.applyTutorResult(tutorResult());
      });

      expect(result.current.state).toEqual(state);
    },
  );

  it.each(["tutor", "quiz"] as const)(
    "%s submission before initial hydration preserves the authoritative snapshot",
    async (operation) => {
      let resolveInitial: ((response: Response) => void) | undefined;
      const durable = lessonState("Durable goal", {
        gate_statuses: { gate: "passed" },
        quiz_states: { quiz: { selected_index: 1, correct: true } },
        due_gate_reviews: [dueReview("gate")],
      });
      let reads = 0;
      vi.stubGlobal(
        "fetch",
        vi.fn(() => {
          reads += 1;
          if (reads === 1) {
            return new Promise<Response>((resolve) => {
              resolveInitial = resolve;
            });
          }
          return Promise.resolve(stateResponse(durable));
        }),
      );
      const session = learner("student-a");
      const { result } = renderHook(() =>
        useLessonState({
          courseId: "course-a",
          lectureId: "lecture-a",
          session,
          mode: "learner",
          enabled: true,
        }),
      );
      await waitFor(() => expect(result.current.loading).toBe(true));

      await act(async () => {
        if (operation === "tutor") await result.current.applyTutorResult(tutorResult());
        else await result.current.applyQuizResult(quizResult());
      });
      expect(result.current.state).toEqual(durable);

      await act(async () => resolveInitial?.(stateResponse(lessonState("Stale"))));
      expect(result.current.state).toEqual(durable);
    },
  );

  it.each([
    ["tutor", "lesson"],
    ["quiz", "lesson"],
    ["tutor", "user"],
    ["quiz", "user"],
  ] as const)("late A %s result cannot cancel %s B hydration", async (operation, switchKind) => {
    let resolveLessonB: ((response: Response) => void) | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        const user = new Headers(init?.headers).get("X-User-Id");
        if (url.includes("lecture-b") || user === "student-b") {
          return new Promise<Response>((resolve) => {
            resolveLessonB = resolve;
          });
        }
        return Promise.resolve(stateResponse(lessonState("Lesson A", {}, "lecture-a")));
      }),
    );
    const sessionA = learner("student-a");
    const { result, rerender } = renderHook(
      ({ lectureId, session }) =>
        useLessonState({
          courseId: "course-a",
          lectureId,
          session,
          mode: "learner",
          enabled: true,
        }),
      { initialProps: { lectureId: "lecture-a", session: sessionA } },
    );
    await waitFor(() => expect(result.current.state?.active_session_goal).toBe("Lesson A"));
    const staleMutation =
      operation === "tutor"
        ? result.current.applyTutorResult.bind(null, tutorResult())
        : result.current.applyQuizResult.bind(null, quizResult());

    const lectureB = switchKind === "lesson" ? "lecture-b" : "lecture-a";
    rerender({
      lectureId: lectureB,
      session: switchKind === "user" ? learner("student-b") : sessionA,
    });
    await waitFor(() => expect(result.current.loading).toBe(true));
    await act(async () => staleMutation());
    await act(async () => resolveLessonB?.(stateResponse(lessonState("Lesson B", {}, lectureB))));

    await waitFor(() => expect(result.current.state?.active_session_goal).toBe("Lesson B"));
  });
});

function learner(username: string): LoginSession {
  return { username, term: "2026", courses: [] };
}

function response(goal: string | null) {
  return stateResponse(lessonState(goal));
}

function lessonState(
  goal: string | null,
  overrides: Partial<LearnerLessonState> = {},
  lectureId = "lecture-a",
): LearnerLessonState {
  return {
    course_id: "course-a",
    lecture_id: lectureId,
    gate_statuses: {},
    quiz_states: {},
    active_session_goal: goal,
    pending_check: null,
    due_gate_reviews: [],
    ...overrides,
  };
}

function stateResponse(state: LearnerLessonState) {
  return new Response(JSON.stringify(state), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function tutorResult() {
  return {
    session_goal: "Model result is not authority",
    quality_gate: { gate_id: "gate", status: "passed" as const },
  };
}

function quizResult() {
  return { block_id: "quiz", selected_index: 1, correct: true };
}

function pendingCheck(gateId: string) {
  return {
    gate_id: gateId,
    gate_revision: "revision-1",
    prompt: "Try the changed case.",
    assistance_level: "none" as const,
    kind: "delayed_transfer" as const,
  };
}

function dueReview(gateId: string) {
  return {
    gate_id: gateId,
    gate_revision: "revision-1",
    due_at: "2026-08-08T10:00:00+00:00",
  };
}
