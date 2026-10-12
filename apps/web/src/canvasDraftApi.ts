import { apiUrl, readApiError } from "./api";
import { authRequestInit } from "./authz";
import {
  isTransientPollResponse,
  pollUntil,
  PollTimeoutError,
  retryAfterMs,
  type PollStep,
} from "./polling";
import type { CanvasGenerationErrorKind } from "./professorCanvasGeneration";
import type { CanvasDocument, LoginSession } from "./types";

export class CanvasDraftRequestError extends Error {
  readonly repairable: boolean;
  readonly terminalGeneration: boolean;
  readonly errorCode?: string;

  constructor(
    message: string,
    terminalGeneration: boolean,
    repairable = false,
    errorCode?: string,
  ) {
    super(message);
    this.name = "CanvasDraftRequestError";
    this.terminalGeneration = terminalGeneration;
    this.repairable = repairable;
    this.errorCode = errorCode;
  }
}

export async function draftLectureCanvas(
  courseId: string,
  lectureId: string,
  session: LoginSession,
  signal?: AbortSignal,
): Promise<CanvasDocument> {
  return requestLectureCanvas(courseId, lectureId, session, "draft", signal);
}

export async function repairLectureCanvas(
  courseId: string,
  lectureId: string,
  session: LoginSession,
  signal?: AbortSignal,
): Promise<CanvasDocument> {
  return requestLectureCanvas(courseId, lectureId, session, "repair", signal);
}

async function requestLectureCanvas(
  courseId: string,
  lectureId: string,
  session: LoginSession,
  action: "draft" | "repair",
  signal?: AbortSignal,
): Promise<CanvasDocument> {
  const storageKey = canvasGenerationStorageKey(courseId, lectureId, action);
  const requestKey = window.sessionStorage.getItem(storageKey) ?? globalThis.crypto.randomUUID();
  window.sessionStorage.setItem(storageKey, requestKey);
  const suffix = action === "repair" ? "/repair" : "";
  const response = await fetch(
    apiUrl(`/admin/courses/${courseId}/lectures/${lectureId}/canvas/draft${suffix}`),
    authRequestInit(session, {
      method: "POST",
      headers: { "Idempotency-Key": requestKey, Prefer: "respond-async" },
      signal,
    }),
  );
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const terminalGeneration = response.headers.get("X-Generation-Status") === "failed";
    if (terminalGeneration && window.sessionStorage.getItem(storageKey) === requestKey) {
      window.sessionStorage.removeItem(storageKey);
    }
    throw new CanvasDraftRequestError(
      readApiError(payload, "Canvas generation request failed."),
      terminalGeneration,
      response.headers.get("X-Generation-Repairable") === "true",
      response.headers.get("X-Generation-Error-Code") ?? undefined,
    );
  }
  let canvas: CanvasDocument;
  try {
    canvas =
      response.status === 202
        ? await pollCanvasGeneration(courseId, lectureId, session, requestKey, signal)
        : (payload as CanvasDocument);
  } catch (error) {
    if (
      error instanceof CanvasDraftRequestError &&
      error.terminalGeneration &&
      window.sessionStorage.getItem(storageKey) === requestKey
    ) {
      window.sessionStorage.removeItem(storageKey);
    }
    throw error;
  }
  if (window.sessionStorage.getItem(storageKey) === requestKey) {
    window.sessionStorage.removeItem(storageKey);
  }
  return canvas;
}

// Jobs may queue behind other authoring work for shared server slots; watch generously.
const DRAFT_POLL_FIRST_MS = 1_500;
const DRAFT_POLL_MAX_MS = 15_000;
const DRAFT_POLL_TIMEOUT_MS = 2 * 60 * 60 * 1000;

async function pollCanvasGeneration(
  courseId: string,
  lectureId: string,
  session: LoginSession,
  requestKey: string,
  signal?: AbortSignal,
): Promise<CanvasDocument> {
  // The job keeps running server-side; an aborted owner (unmount, logout) only stops watching.
  try {
    return await pollUntil({
      initialDelayMs: DRAFT_POLL_FIRST_MS,
      maxDelayMs: DRAFT_POLL_MAX_MS,
      timeoutMs: DRAFT_POLL_TIMEOUT_MS,
      signal,
      poll: (pollSignal) =>
        readGenerationStatus(courseId, lectureId, session, requestKey, pollSignal),
    });
  } catch (error) {
    if (!(error instanceof PollTimeoutError)) throw error;
    throw new CanvasDraftRequestError(
      "Canvas generation is still in progress on the server. Reload to keep following it.",
      false,
    );
  }
}

async function readGenerationStatus(
  courseId: string,
  lectureId: string,
  session: LoginSession,
  requestKey: string,
  signal: AbortSignal | undefined,
): Promise<PollStep<CanvasDocument>> {
  const response = await fetch(
    apiUrl(`/admin/courses/${courseId}/lectures/${lectureId}/canvas/draft/status`),
    authRequestInit(session, { headers: { "Idempotency-Key": requestKey }, signal }),
  );
  if (isTransientPollResponse(response)) {
    return { done: false, retryAfterMs: retryAfterMs(response) };
  }
  const status = await response.json().catch(() => null);
  if (!response.ok) {
    throw new CanvasDraftRequestError(
      readApiError(status, "Could not read generation progress."),
      false,
    );
  }
  if (status?.status === "failed") {
    throw new CanvasDraftRequestError(
      status.error_detail ?? "Canvas generation failed.",
      true,
      status.repairable === true,
      typeof status.error_code === "string" ? status.error_code : undefined,
    );
  }
  if (status?.status === "completed" && status.canvas) return { done: true, value: status.canvas };
  if (status?.status !== "running") {
    throw new CanvasDraftRequestError("Invalid canvas generation status.", false);
  }
  return { done: false };
}

/** An interrupted job (lost worker) or lost connection resumes under its key; failures restart. */
export function retryStartsFresh(progress: { errorKind?: CanvasGenerationErrorKind }) {
  return progress.errorKind !== "interrupted" && progress.errorKind !== "network";
}

/** A retry after a failed attempt is a new request: forget the replayable idempotency keys. */
export function forgetCanvasGenerationRequest(courseId: string, lectureId: string) {
  for (const action of ["draft", "repair"] as const) {
    window.sessionStorage.removeItem(canvasGenerationStorageKey(courseId, lectureId, action));
  }
}

function canvasGenerationStorageKey(
  courseId: string,
  lectureId: string,
  action: "draft" | "repair",
) {
  return `lecturepilot:canvas-generation:${courseId}:${lectureId}:${action}`;
}
