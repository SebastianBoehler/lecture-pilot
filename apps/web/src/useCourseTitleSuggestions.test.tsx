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
          personalCourses: [
            {
              source: "ilias",
              external_course_id: "crs:42",
              term: "Sommer 2026",
              title: "Personal Course",
            },
          ],
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
    expect(result.current.courseSuggestions).toEqual([
      {
        title: "Personal Course",
        sources: ["ilias_membership"],
      },
      {
        instructor: null,
        number: "INFO-1234",
        title: "Machine Learning",
        sources: ["alma_catalog"],
      },
    ]);
    expect(result.current.courseSearchFailed).toBe(false);
  });

  it("keeps personal suggestions when the public Alma catalogue is unavailable", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 502 })));

    const { result } = renderHook(() =>
      useCourseTitleSuggestions({
        enabled: true,
        personalCourses: [
          {
            source: "alma",
            external_course_id: "title:42",
            term: "Sommer 2026",
            title: "Personal Course",
          },
        ],
        query: "Mach",
        session: localProfessorSession,
      }),
    );

    await act(() => vi.advanceTimersByTimeAsync(COURSE_SEARCH_DEBOUNCE_MS));

    expect(result.current.courseSuggestions).toEqual([
      { title: "Personal Course", sources: ["alma_timetable"] },
    ]);
    expect(result.current.courseSearchFailed).toBe(true);
  });
});
