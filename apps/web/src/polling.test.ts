import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { pollUntil, PollTimeoutError, retryAfterMs } from "./polling";

let visibility: DocumentVisibilityState = "visible";

beforeEach(() => {
  vi.useFakeTimers();
  visibility = "visible";
  vi.spyOn(document, "visibilityState", "get").mockImplementation(() => visibility);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

function requestTimes(stopAfter = Infinity) {
  const times: number[] = [];
  const started = Date.now();
  const poll = vi.fn(async () => {
    times.push(Date.now() - started);
    return times.length >= stopAfter
      ? { done: true as const, value: "ready" }
      : { done: false as const };
  });
  return { poll, times };
}

it("backs off exponentially up to the maximum delay", async () => {
  const { poll, times } = requestTimes(5);
  const result = pollUntil({
    poll,
    initialDelayMs: 1_000,
    maxDelayMs: 3_000,
    timeoutMs: 60_000,
    backoffFactor: 2,
  });
  await vi.advanceTimersByTimeAsync(20_000);
  await expect(result).resolves.toBe("ready");
  expect(times).toEqual([1_000, 3_000, 6_000, 9_000, 12_000]);
});

it("rejects after the overall deadline", async () => {
  const { poll } = requestTimes();
  const result = pollUntil({ poll, initialDelayMs: 1_000, maxDelayMs: 1_000, timeoutMs: 2_500 });
  const rejected = expect(result).rejects.toBeInstanceOf(PollTimeoutError);
  await vi.advanceTimersByTimeAsync(5_000);
  await rejected;
  expect(poll).toHaveBeenCalledTimes(3);
});

it("stops requesting once aborted, e.g. on unmount", async () => {
  const { poll } = requestTimes();
  const controller = new AbortController();
  const result = pollUntil({
    poll,
    initialDelayMs: 1_000,
    maxDelayMs: 1_000,
    timeoutMs: 60_000,
    signal: controller.signal,
  });
  const rejected = expect(result).rejects.toMatchObject({ name: "AbortError" });
  await vi.advanceTimersByTimeAsync(2_500);
  controller.abort();
  await vi.advanceTimersByTimeAsync(10_000);
  await rejected;
  expect(poll).toHaveBeenCalledTimes(2);
});

it("pauses while the document is hidden and resumes when visible", async () => {
  const { poll, times } = requestTimes(2);
  const result = pollUntil({ poll, initialDelayMs: 1_000, maxDelayMs: 1_000, timeoutMs: 60_000 });
  await vi.advanceTimersByTimeAsync(1_000);
  visibility = "hidden";
  await vi.advanceTimersByTimeAsync(30_000);
  expect(poll).toHaveBeenCalledTimes(1);
  visibility = "visible";
  document.dispatchEvent(new Event("visibilitychange"));
  await expect(result).resolves.toBe("ready");
  expect(times).toEqual([1_000, 31_000]);
});

it("polls once more after a long hidden pause before reporting the deadline", async () => {
  const { poll } = requestTimes(2);
  const result = pollUntil({ poll, initialDelayMs: 1_000, maxDelayMs: 1_000, timeoutMs: 5_000 });
  await vi.advanceTimersByTimeAsync(1_000);
  visibility = "hidden";
  await vi.advanceTimersByTimeAsync(60_000);
  visibility = "visible";
  document.dispatchEvent(new Event("visibilitychange"));
  await expect(result).resolves.toBe("ready");
});

it("waits at least as long as a Retry-After asks", async () => {
  const times: number[] = [];
  const started = Date.now();
  const poll = vi.fn(async () => {
    times.push(Date.now() - started);
    return times.length === 1
      ? { done: false as const, retryAfterMs: 10_000 }
      : { done: true as const, value: "ready" };
  });
  const result = pollUntil({ poll, initialDelayMs: 1_000, maxDelayMs: 2_000, timeoutMs: 60_000 });
  await vi.advanceTimersByTimeAsync(12_000);
  await expect(result).resolves.toBe("ready");
  expect(times).toEqual([1_000, 11_000]);
});

it("reads Retry-After seconds or dates only from 429 and 503 responses", () => {
  const limited = new Response(null, { status: 429, headers: { "Retry-After": "7" } });
  const unavailable = new Response(null, {
    status: 503,
    headers: { "Retry-After": new Date(Date.now() + 4_000).toUTCString() },
  });
  const ok = new Response(null, { status: 200, headers: { "Retry-After": "7" } });
  expect(retryAfterMs(limited)).toBe(7_000);
  expect(retryAfterMs(unavailable)).toBeGreaterThan(2_000);
  expect(retryAfterMs(ok)).toBeUndefined();
});
