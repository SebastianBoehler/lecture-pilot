import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { professorFetchMock } from "./ProfessorCourseBuilder.testFixtures";
import type { ProfessorCourseBuilderProps } from "./useProfessorCourseBuilder";
import { useProfessorCourseBuilder } from "./useProfessorCourseBuilder";
import type { LoginSession } from "./types";

const session: LoginSession = {
  account_type: "professor",
  courses: [],
  roles: ["professor"],
  term: "Sommer 2026",
  username: "professor-demo",
};

const hookProps: ProfessorCourseBuilderProps = {
  onPublishWorkspace: vi.fn(),
  onWorkspacePublished: vi.fn(),
  previewWorkspaceUrl: (_courseId, lecture) => `/preview/${lecture.id}`,
  publishedLectureIds: [],
  session,
};

describe("Professor course builder restoration", () => {
  afterEach(() => {
    window.sessionStorage.clear();
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it("restores only completed full-course drafts and offers AI repair for missing ones", async () => {
    saveRestorableFullCourse();
    const baseFetch = professorFetchMock();
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (init?.method !== "POST" && url.includes("/lectures/lecture-02/canvas/draft")) {
          return Promise.resolve(response({ detail: "Canvas draft not found." }, false, true));
        }
        return baseFetch(url, init);
      }),
    );

    const { result } = renderHook(() => useProfessorCourseBuilder(hookProps));

    await waitFor(() => expect(result.current.isRestoring).toBe(false));
    await waitFor(() => expect(result.current.generateStep.generatedCount).toBe(1));
    expect(result.current.generateStep.previewLectures).toEqual([
      expect.objectContaining({ id: "lecture-01" }),
    ]);
    expect(result.current.generateStep.generationProgress).toEqual([
      { lectureId: "lecture-01", status: "ready" },
      expect.objectContaining({
        errorKind: "repair",
        lectureId: "lecture-02",
        status: "error",
      }),
    ]);
  });
});

function saveRestorableFullCourse() {
  window.sessionStorage.setItem(
    "lecturepilot.professor-builder.current",
    JSON.stringify({
      bundleReady: true,
      canvasReady: true,
      courseReady: true,
      lectureSchedule: [],
      query: "",
      setup: {
        accessPolicy: "tuebingen_enrolled",
        courseTitle: "Demo ML Course",
        firstLectureDate: "2026-05-06",
        lectureCount: "",
        lectureNumber: "",
        lectureTitle: "",
        target: "full-course",
      },
      workspace: { courseId: "demo-ml-course", lectureId: "lecture-01" },
    }),
  );
}

function response(payload: unknown, ok = true, repairable = false) {
  return new Response(JSON.stringify(payload), {
    status: ok ? 200 : 404,
    headers: repairable ? { "X-Generation-Repairable": "true" } : undefined,
  });
}
