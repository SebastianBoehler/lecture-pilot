import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { useRestoredGenerationPolling } from "./useRestoredGenerationPolling";
import type { LoginSession } from "../shared/types";

const session: LoginSession = { courses: [], term: "Sommer 2026", username: "professor-demo" };

afterEach(() => vi.unstubAllGlobals());

it("keeps following a restored running job until its draft is ready", async () => {
  let calls = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      calls += 1;
      if (calls === 1) {
        return new Response(JSON.stringify({ detail: "Generation is running." }), {
          status: 404,
          headers: { "X-Generation-Status": "running" },
        });
      }
      return Response.json({ id: "draft", title: "Lecture 02", sections: [], warnings: [] });
    }),
  );
  const onProgress = vi.fn();
  const onDraftReady = vi.fn();
  const onSettled = vi.fn();
  renderHook(() =>
    useRestoredGenerationPolling({
      courseId: "course",
      lectureIds: ["lecture-02"],
      session,
      intervalMs: 10,
      onDraftReady,
      onProgress,
      onSettled,
      onError: vi.fn(),
    }),
  );
  await waitFor(() => expect(onSettled).toHaveBeenCalledWith("lecture-02"));
  expect(onProgress).toHaveBeenCalledWith({ lectureId: "lecture-02", status: "generating" });
  expect(onProgress).toHaveBeenCalledWith({ lectureId: "lecture-02", status: "ready" });
  expect(onDraftReady).toHaveBeenCalled();
});

it("reports a connection failure without claiming the job failed", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
  const onError = vi.fn();
  const onSettled = vi.fn();
  renderHook(() =>
    useRestoredGenerationPolling({
      courseId: "course",
      lectureIds: ["lecture-02"],
      session,
      intervalMs: 10,
      onDraftReady: vi.fn(),
      onProgress: vi.fn(),
      onSettled,
      onError,
    }),
  );
  await waitFor(() => expect(onError).toHaveBeenCalledWith(expect.stringContaining("reconnect")));
  expect(onSettled).not.toHaveBeenCalled();
});

it("ignores an in-flight response after the polling context is removed", async () => {
  let resolve!: (response: Response) => void;
  const fetch = vi.fn(
    () =>
      new Promise<Response>((done) => {
        resolve = done;
      }),
  );
  vi.stubGlobal("fetch", fetch);
  const onDraftReady = vi.fn();
  const onProgress = vi.fn();
  const { unmount } = renderHook(() =>
    useRestoredGenerationPolling({
      courseId: "course",
      lectureIds: ["lecture-02"],
      session,
      intervalMs: 10,
      onDraftReady,
      onProgress,
      onSettled: vi.fn(),
      onError: vi.fn(),
    }),
  );
  await waitFor(() => expect(fetch).toHaveBeenCalled());
  unmount();
  resolve(Response.json({ id: "draft", title: "Lecture 02", sections: [], warnings: [] }));
  await new Promise((done) => setTimeout(done, 20));
  expect(onDraftReady).not.toHaveBeenCalled();
  expect(onProgress).not.toHaveBeenCalled();
});
