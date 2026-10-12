import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { professorFetchMock } from "./ProfessorCourseBuilder.testFixtures";
import { readSavedFlow, writeResumeFlow } from "./professorBuilderState";
import type { ProfessorCourseBuilderProps } from "./useProfessorCourseBuilder";
import { useProfessorCourseBuilder } from "./useProfessorCourseBuilder";
import { I18nWrapper } from "../test/renderWithI18n";
import type { CourseWorkspaceResult, Lecture, LoginSession } from "../shared/types";

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
  session,
};

function lecture(id: string, number: string): Lecture {
  return { id, number, title: `Lecture ${number}`, date: "2026-05-06", attendance: "unknown" };
}

const fullCourse: CourseWorkspaceResult = {
  course: {
    id: "demo-ml-course",
    title: "Demo ML Course",
    professor: "Prof",
    term: "Sommer 2026",
    canvas_language: "de",
  },
  lectures: [lecture("lecture-01", "01"), lecture("lecture-02", "02")],
  active_lecture_id: "lecture-01",
};

afterEach(() => {
  window.sessionStorage.clear();
  vi.unstubAllGlobals();
});

it("writes a backend-restorable flow for an unfinished course", () => {
  writeResumeFlow(fullCourse);
  const flow = readSavedFlow();
  expect(flow.workspace).toEqual({ courseId: "demo-ml-course", lectureId: "lecture-01" });
  expect(flow.setup).toMatchObject({
    courseTitle: "Demo ML Course",
    canvasLanguage: "de",
    target: "full-course",
  });
  expect(flow.courseReady && flow.bundleReady).toBe(true);
});

it("resumes a confirmed course at the learning plan instead of optional media", async () => {
  writeResumeFlow(fullCourse);
  const base = professorFetchMock();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.includes("/canvas/draft") && !init?.method) {
        return new Response(JSON.stringify({ detail: "Canvas draft not found." }), { status: 404 });
      }
      const result = await base(url, init);
      if (url.endsWith("/source-routing") && !init?.method) {
        return new Response(
          JSON.stringify({
            ...((await result.json()) as Record<string, unknown>),
            confirmed: true,
          }),
        );
      }
      return result;
    }),
  );
  const { result } = renderHook(() => useProfessorCourseBuilder(hookProps), {
    wrapper: I18nWrapper,
  });
  await waitFor(() => expect(result.current.isRestoring).toBe(false));
  expect(result.current.activeStep).toBe("design");
  expect(result.current.error).toBeNull();
});

it("resumes a course without uploads at the materials upload", async () => {
  writeResumeFlow(fullCourse);
  const base = professorFetchMock();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const result = await base(url, init);
      if (url.includes("/source-bundle")) {
        return new Response(
          JSON.stringify({ ...((await result.json()) as Record<string, unknown>), files: [] }),
        );
      }
      return result;
    }),
  );
  const { result } = renderHook(() => useProfessorCourseBuilder(hookProps), {
    wrapper: I18nWrapper,
  });
  await waitFor(() => expect(result.current.isRestoring).toBe(false));
  expect(result.current.activeStep).toBe("upload");
});

it("resumes an unscheduled full course despite its single placeholder lecture", () => {
  writeResumeFlow({
    ...fullCourse,
    lectures: [{ ...lecture("lecture-01", "01"), title: "Lecture 01" }],
  });
  expect(readSavedFlow().setup.target).toBe("full-course");
  writeResumeFlow({
    ...fullCourse,
    lectures: [{ ...lecture("lecture-03", "03"), title: "Bayesian decision theory" }],
    setup_target: null,
  });
  expect(readSavedFlow().setup).toMatchObject({ target: "single-lecture", lectureNumber: "03" });
  writeResumeFlow({
    ...fullCourse,
    lectures: [lecture("lecture-03", "03")],
    setup_target: "full-course",
  });
  expect(readSavedFlow().setup.target).toBe("full-course");
});

it("resumes at review and publish when drafts failed, so retry is the next action", async () => {
  writeResumeFlow(fullCourse);
  const base = professorFetchMock();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.includes("/canvas/draft") && !init?.method) {
        return new Response(JSON.stringify({ detail: "Model request timed out." }), {
          status: 404,
          headers: { "X-Generation-Status": "failed", "X-Generation-Repairable": "false" },
        });
      }
      const result = await base(url, init);
      if (url.endsWith("/source-routing") && !init?.method) {
        return new Response(
          JSON.stringify({
            ...((await result.json()) as Record<string, unknown>),
            confirmed: true,
          }),
        );
      }
      return result;
    }),
  );
  const { result } = renderHook(() => useProfessorCourseBuilder(hookProps), {
    wrapper: I18nWrapper,
  });
  await waitFor(() => expect(result.current.isRestoring).toBe(false));
  expect(result.current.activeStep).toBe("generate");
});
