import { act, renderHook, waitFor } from "@testing-library/react";
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
  previewWorkspaceUrl: () => "/preview",
  publishedLectureIds: [],
  session,
};

describe("Professor course builder upload invalidation", () => {
  afterEach(() => {
    window.sessionStorage.clear();
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it("invalidates a restored draft when one file uploads before a batch failure", async () => {
    saveRestorableFlow("single-lecture");
    const baseFetch = professorFetchMock();
    let successfulUploads = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes("/materials")) {
          const path = String((init?.body as FormData).get("path"));
          if (path.endsWith("failed.md")) {
            return Promise.resolve(response({ detail: "The backend is unavailable." }, false));
          }
          successfulUploads += 1;
        }
        return baseFetch(url, init);
      }),
    );
    const { result } = renderHook(() => useProfessorCourseBuilder(hookProps));
    await restoredDraft(result);

    act(() => {
      result.current.uploadStep.onUploadFilesChange([
        new File(["ready"], "ready.md"),
        new File(["failed"], "failed.md"),
      ]);
    });
    await waitFor(() => expect(result.current.uploadStep.uploadFiles).toHaveLength(2));
    await act(async () => {
      await result.current.uploadStep.onUpload();
    });

    expect(successfulUploads).toBe(1);
    expect(result.current.error).toMatch(/failed\.md.*backend is unavailable/i);
    expect(result.current.generateStep.canvas).toBeNull();
    expect(result.current.generateStep.generatedCount).toBe(0);
    expect(result.current.publishStep.canPublish).toBe(false);
  });

  it("invalidates a restored draft before schedule generation finishes", async () => {
    saveRestorableFlow("full-course");
    const baseFetch = professorFetchMock();
    let resolveSchedule: ((value: Response) => void) | undefined;
    const scheduleResponse = new Promise<Response>((resolve) => {
      resolveSchedule = resolve;
    });
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes("/lecture-schedule")) return scheduleResponse;
        return baseFetch(url, init);
      }),
    );
    const { result } = renderHook(() => useProfessorCourseBuilder(hookProps));
    await restoredDraft(result);

    act(() => {
      result.current.uploadStep.onUploadFilesChange([new File(["ready"], "ready.md")]);
    });
    await waitFor(() => expect(result.current.uploadStep.uploadFiles).toHaveLength(1));
    let upload: Promise<void>;
    act(() => {
      upload = result.current.uploadStep.onUpload();
    });
    await waitFor(() => expect(resolveSchedule).toBeDefined());

    await waitFor(() => expect(result.current.generateStep.canvas).toBeNull());
    expect(result.current.generateStep.generatedCount).toBe(0);
    expect(result.current.publishStep.canPublish).toBe(false);

    resolveSchedule?.(response({ detail: "Schedule generation failed." }, false));
    await act(async () => {
      await upload;
    });
    expect(result.current.error).toMatch(/schedule generation failed/i);
  });

  it("invalidates a restored draft when source-bundle refresh fails after upload", async () => {
    saveRestorableFlow("single-lecture");
    const baseFetch = professorFetchMock();
    let sourceBundleRequests = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes("/source-bundle")) {
          sourceBundleRequests += 1;
          if (sourceBundleRequests === 2) {
            return Promise.resolve(response({ detail: "Source index refresh failed." }, false));
          }
        }
        return baseFetch(url, init);
      }),
    );
    const { result } = renderHook(() => useProfessorCourseBuilder(hookProps));
    await restoredDraft(result);

    act(() => {
      result.current.uploadStep.onUploadFilesChange([new File(["ready"], "ready.md")]);
    });
    await waitFor(() => expect(result.current.uploadStep.uploadFiles).toHaveLength(1));
    await act(async () => {
      await result.current.uploadStep.onUpload();
    });

    expect(sourceBundleRequests).toBe(2);
    expect(result.current.error).toMatch(/source index refresh failed/i);
    expect(result.current.generateStep.canvas).toBeNull();
    expect(result.current.generateStep.generatedCount).toBe(0);
    expect(result.current.publishStep.canPublish).toBe(false);
  });

  it("invalidates a restored draft when an upload response is lost", async () => {
    saveRestorableFlow("single-lecture");
    const baseFetch = professorFetchMock();
    let sourceBundleRequests = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes("/materials")) return Promise.reject(new TypeError("Failed to fetch"));
        if (url.includes("/source-bundle")) {
          sourceBundleRequests += 1;
          if (sourceBundleRequests === 2) {
            return Promise.resolve(
              response({
                course_id: "demo-ml-course",
                counts_by_kind: { markdown: 1 },
                files: [{ path: "uploads/ready.md", kind: "markdown", size_bytes: 5 }],
              }),
            );
          }
        }
        return baseFetch(url, init);
      }),
    );
    const { result } = renderHook(() => useProfessorCourseBuilder(hookProps));
    await restoredDraft(result);

    await uploadFiles(result, [new File(["ready"], "ready.md")]);

    expect(result.current.error).toMatch(/ready\.md.*failed to fetch/i);
    expect(result.current.uploadStep.bundle?.files.map((file) => file.path)).toEqual([
      "uploads/ready.md",
    ]);
    expectInvalidated(result);
  });

  it("invalidates a restored draft when upload and source refresh responses fail", async () => {
    saveRestorableFlow("single-lecture");
    const baseFetch = professorFetchMock();
    let sourceBundleRequests = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes("/materials")) return Promise.reject(new TypeError("Failed to fetch"));
        if (url.includes("/source-bundle")) {
          sourceBundleRequests += 1;
          if (sourceBundleRequests === 2) {
            return Promise.resolve(response({ detail: "Source index refresh failed." }, false));
          }
        }
        return baseFetch(url, init);
      }),
    );
    const { result } = renderHook(() => useProfessorCourseBuilder(hookProps));
    await restoredDraft(result);

    await uploadFiles(result, [new File(["ready"], "ready.md")]);

    expect(result.current.error).toMatch(/failed to fetch.*source.*refresh.*failed/i);
    expectInvalidated(result);
  });
});

type BuilderHookResult = ReturnType<
  typeof renderHook<ReturnType<typeof useProfessorCourseBuilder>, unknown>
>["result"];

async function uploadFiles(result: BuilderHookResult, files: File[]) {
  act(() => {
    result.current.uploadStep.onUploadFilesChange(files);
  });
  await waitFor(() => expect(result.current.uploadStep.uploadFiles).toHaveLength(files.length));
  await act(async () => {
    await result.current.uploadStep.onUpload();
  });
}

function expectInvalidated(result: BuilderHookResult) {
  expect(result.current.generateStep.canvas).toBeNull();
  expect(result.current.generateStep.generatedCount).toBe(0);
  expect(result.current.publishStep.canPublish).toBe(false);
}

async function restoredDraft(result: BuilderHookResult) {
  await waitFor(() => expect(result.current.generateStep.canvas).not.toBeNull());
  expect(result.current.publishStep.canPublish).toBe(true);
  expect(result.current.generateStep.generatedCount).toBeGreaterThan(0);
}

function saveRestorableFlow(target: "full-course" | "single-lecture") {
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
        lectureNumber: "03",
        lectureTitle: "Bayesian Decision Theory",
        target,
      },
      workspace: { courseId: "demo-ml-course", lectureId: "lecture-03" },
    }),
  );
}

function response(payload: unknown, ok = true) {
  return { ok, json: async () => payload } as Response;
}
