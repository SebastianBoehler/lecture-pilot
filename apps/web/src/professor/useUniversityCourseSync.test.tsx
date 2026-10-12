import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { localProfessorSession } from "../shell/appDefaults";
import { useUniversityCourseSync } from "./useUniversityCourseSync";

describe("university course synchronization", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("publishes one source while another source is still loading", async () => {
    vi.useFakeTimers();
    const partial = {
      ...localProfessorSession,
      university_course_sync_status: "loading" as const,
      university_course_source_statuses: { alma: "loading" as const, ilias: "ready" as const },
      university_courses: [
        {
          source: "ilias" as const,
          external_course_id: "crs:42",
          term: localProfessorSession.term,
          title: "Reliable Systems",
        },
      ],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(partial), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    const setSession = vi.fn();

    renderHook(() =>
      useUniversityCourseSync(
        { ...localProfessorSession, university_course_sync_status: "loading" },
        setSession,
      ),
    );
    await act(() => vi.advanceTimersByTimeAsync(2_000));

    expect(setSession).toHaveBeenCalledWith(expect.objectContaining(partial));
  });

  it("backs off while loading, stops on unmount and reports a timeout", async () => {
    vi.useFakeTimers();
    const loading = { ...localProfessorSession, university_course_sync_status: "loading" as const };
    const fetchMock = vi.fn(async () => Response.json(loading));
    vi.stubGlobal("fetch", fetchMock);
    const setSession = vi.fn();

    const { unmount } = renderHook(() => useUniversityCourseSync(loading, setSession));
    await act(() => vi.advanceTimersByTimeAsync(5_000));
    expect(fetchMock).toHaveBeenCalledTimes(2); // at 2 s and 5 s, not every 750 ms
    await act(() => vi.advanceTimersByTimeAsync(60_000));
    expect(setSession).toHaveBeenLastCalledWith(
      expect.objectContaining({ university_course_sync_status: "error" }),
    );
    const requests = fetchMock.mock.calls.length;
    expect(requests).toBeLessThan(12);

    unmount();
    await act(() => vi.advanceTimersByTimeAsync(60_000));
    expect(fetchMock).toHaveBeenCalledTimes(requests);
  });
});
