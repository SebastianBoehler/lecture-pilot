import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { localProfessorSession } from "../shell/appDefaults";
import { json, lecture, mockApi, states } from "./coursePageTestFixtures";
import type { CourseLectureStates } from "./courseLectureStateTypes";
import { useCourseLectureStates } from "./useCourseLectureStates";

const busy = states([lecture("lecture-01", { draft: "generating", next_action: "wait" })]);
const idle = states([lecture("lecture-01", { draft: "ready", next_action: "review_draft" })]);

function serve(sequence: CourseLectureStates[]) {
  let index = 0;
  return mockApi({
    "GET /lecture-states": () => json(sequence[Math.min(index++, sequence.length - 1)]),
  });
}

function setVisibility(state: DocumentVisibilityState) {
  Object.defineProperty(document, "visibilityState", { configurable: true, value: state });
  document.dispatchEvent(new Event("visibilitychange"));
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  setVisibility("visible");
});

describe("useCourseLectureStates polling", () => {
  it("polls while a lecture is busy and stops once every lecture is idle", async () => {
    const fetchMock = serve([busy, busy, idle]);
    const { result } = renderHook(() =>
      useCourseLectureStates("machine-learning", localProfessorSession),
    );
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(result.current.busy).toBe(true);

    await act(() => vi.advanceTimersByTimeAsync(2_000));
    expect(fetchMock).toHaveBeenCalledTimes(2);
    await act(() => vi.advanceTimersByTimeAsync(3_000));
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(result.current.busy).toBe(false);
    expect(result.current.states?.lectures[0].next_action).toBe("review_draft");

    await act(() => vi.advanceTimersByTimeAsync(120_000));
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("does not poll when nothing is running", async () => {
    const fetchMock = serve([idle]);
    renderHook(() => useCourseLectureStates("machine-learning", localProfessorSession));
    await act(() => vi.advanceTimersByTimeAsync(60_000));
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("pauses in hidden tabs and resumes when the tab is visible again", async () => {
    const fetchMock = serve([busy, idle]);
    renderHook(() => useCourseLectureStates("machine-learning", localProfessorSession));
    await act(() => vi.advanceTimersByTimeAsync(0));
    setVisibility("hidden");
    await act(() => vi.advanceTimersByTimeAsync(60_000));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await act(async () => setVisibility("visible"));
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("keeps polling through a transient server error", async () => {
    let index = 0;
    const fetchMock = mockApi({
      "GET /lecture-states": () =>
        [json(busy), json({ detail: "Busy." }, 503), json(idle)][Math.min(index++, 2)],
    });
    const { result } = renderHook(() =>
      useCourseLectureStates("machine-learning", localProfessorSession),
    );
    await act(() => vi.advanceTimersByTimeAsync(0));
    await act(() => vi.advanceTimersByTimeAsync(10_000));
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(result.current.busy).toBe(false);
    expect(result.current.error).toBeNull();
  });
});
