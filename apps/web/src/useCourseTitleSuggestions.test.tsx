import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { localProfessorSession } from "./appDefaults";
import { COURSE_SEARCH_DEBOUNCE_MS, useCourseTitleSuggestions } from "./useCourseTitleSuggestions";

describe("course title suggestions", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("debounces public Alma search while preserving personal suggestions", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [{ title: "Machine Learning", number: "INFO-1234", instructor: null }],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { result, rerender } = renderHook(
      ({ query }) =>
        useCourseTitleSuggestions({
          enabled: true,
          personalTitles: ["Personal Course"],
          query,
          session: localProfessorSession,
        }),
      { initialProps: { query: "Ma" } },
    );

    await act(() => vi.advanceTimersByTimeAsync(COURSE_SEARCH_DEBOUNCE_MS));
    expect(fetchMock).not.toHaveBeenCalled();

    rerender({ query: "Mach" });
    await act(() => vi.advanceTimersByTimeAsync(COURSE_SEARCH_DEBOUNCE_MS - 1));
    expect(fetchMock).not.toHaveBeenCalled();

    await act(() => vi.advanceTimersByTimeAsync(1));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("q=Mach");
    expect(result.current.courseSuggestions).toEqual(["Personal Course", "Machine Learning"]);
    expect(result.current.courseSearchFailed).toBe(false);
  });
});
