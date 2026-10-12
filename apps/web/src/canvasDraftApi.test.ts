import { afterEach, expect, it, vi } from "vitest";

import {
  draftLectureCanvas,
  forgetCanvasGenerationRequest,
  retryStartsFresh,
} from "./canvasDraftApi";
import type { LoginSession } from "./types";

const session: LoginSession = { username: "professor-demo", term: "2026", courses: [] };

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  window.sessionStorage.clear();
});

it("stops polling generation progress once its owner aborts, e.g. on logout", async () => {
  vi.useFakeTimers();
  const fetchMock = vi.fn(async (url: string) =>
    url.endsWith("/status")
      ? new Response(JSON.stringify({ status: "running" }))
      : new Response(JSON.stringify({ status: "running" }), { status: 202 }),
  );
  vi.stubGlobal("fetch", fetchMock);
  const controller = new AbortController();
  const draft = draftLectureCanvas("course", "lecture-01", session, controller.signal);
  const rejected = expect(draft).rejects.toMatchObject({ name: "AbortError" });
  await vi.advanceTimersByTimeAsync(3_750); // status polls at 1.5 s and 3.75 s (backoff)
  expect(fetchMock).toHaveBeenCalledTimes(3);

  controller.abort();
  await vi.advanceTimersByTimeAsync(10_000);
  await rejected;
  expect(fetchMock).toHaveBeenCalledTimes(3);
});

it("starts a new request after a failure the page never observed", async () => {
  const keys: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (_url: string, init?: RequestInit) => {
      keys.push(new Headers(init?.headers).get("Idempotency-Key") ?? "");
      return new Response(JSON.stringify({ id: "canvas", sections: [] }), { status: 200 });
    }),
  );
  // A key left behind by a job that failed while the page was closed or reloading.
  window.sessionStorage.setItem(
    "lecturepilot:canvas-generation:course:lecture-01:draft",
    "stale-key",
  );

  forgetCanvasGenerationRequest("course", "lecture-01");
  await draftLectureCanvas("course", "lecture-01", session);

  expect(keys).toHaveLength(1);
  expect(keys[0]).not.toBe("stale-key");
});

it("keeps the request key of an interrupted job so a retry resumes it", () => {
  const key = "lecturepilot:canvas-generation:course:lecture-01:draft";
  window.sessionStorage.setItem(key, "resume-key");
  expect(retryStartsFresh({ errorKind: "interrupted" })).toBe(false);
  expect(retryStartsFresh({ errorKind: "service" })).toBe(true);
  expect(retryStartsFresh({ errorKind: "repair" })).toBe(true);
  expect(window.sessionStorage.getItem(key)).toBe("resume-key");
});
