import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  FEEDBACK_TURN_THRESHOLD,
  feedbackPromptStorageKey,
  useFeedbackPrompt,
} from "./useFeedbackPrompt";
import type { LoginSession } from "./types";

describe("feedback prompt", () => {
  it("opens once after enough successful student tutor turns", () => {
    const session = studentSession();
    const firstVisit = renderHook(() => useFeedbackPrompt(session, true));

    for (let turn = 1; turn < FEEDBACK_TURN_THRESHOLD; turn += 1) {
      act(() => firstVisit.result.current.recordSuccessfulTutorTurn());
      expect(firstVisit.result.current.source).toBeNull();
    }
    act(() => firstVisit.result.current.recordSuccessfulTutorTurn());
    expect(firstVisit.result.current.source).toBeNull();
    firstVisit.unmount();

    const nextVisit = renderHook(() => useFeedbackPrompt(session, true));
    expect(nextVisit.result.current.source).toBe("threshold");
    act(() => nextVisit.result.current.close());
    for (let turn = 0; turn < FEEDBACK_TURN_THRESHOLD; turn += 1) {
      act(() => nextVisit.result.current.recordSuccessfulTutorTurn());
    }
    expect(nextVisit.result.current.source).toBeNull();
  });

  it("never automatically prompts professors but still supports the manual entry point", () => {
    const { result } = renderHook(() => useFeedbackPrompt(professorSession()));

    for (let turn = 0; turn < FEEDBACK_TURN_THRESHOLD; turn += 1) {
      act(() => result.current.recordSuccessfulTutorTurn());
    }
    expect(result.current.source).toBeNull();
    expect(window.localStorage).toHaveLength(0);

    act(() => result.current.openManually());
    expect(result.current.source).toBe("manual");
  });

  it("persists the threshold state per signed-in student", () => {
    const session = studentSession();
    const key = feedbackPromptStorageKey(session.username);
    window.localStorage.setItem(
      key,
      JSON.stringify({
        prompted: false,
        qualifiedVisitId: "earlier-visit",
        successfulTurns: FEEDBACK_TURN_THRESHOLD - 1,
      }),
    );
    const firstVisit = renderHook(() => useFeedbackPrompt(session, true));

    act(() => firstVisit.result.current.recordSuccessfulTutorTurn());

    expect(firstVisit.result.current.source).toBeNull();
    expect(JSON.parse(String(window.localStorage.getItem(key)))).toMatchObject({
      prompted: false,
      successfulTurns: FEEDBACK_TURN_THRESHOLD,
    });
    firstVisit.unmount();

    const nextVisit = renderHook(() => useFeedbackPrompt(session, true));
    expect(nextVisit.result.current.source).toBe("threshold");
    expect(JSON.parse(String(window.localStorage.getItem(key)))).toMatchObject({
      prompted: true,
      successfulTurns: FEEDBACK_TURN_THRESHOLD,
    });
  });
});

function studentSession(): LoginSession {
  return {
    account_type: "student",
    auth_transport: "cookie",
    courses: [],
    roles: ["student"],
    term: "Sommer 2026",
    username: "student-one",
  };
}

function professorSession(): LoginSession {
  return {
    ...studentSession(),
    account_type: "professor",
    roles: ["professor"],
    username: "professor-one",
  };
}
