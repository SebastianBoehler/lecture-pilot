import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { localProfessorSession } from "./appDefaults";
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
    await act(() => vi.advanceTimersByTimeAsync(750));

    expect(setSession).toHaveBeenCalledWith(expect.objectContaining(partial));
  });
});
