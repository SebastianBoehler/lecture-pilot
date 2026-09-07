import { apiUrl, readApiError } from "./api";
import { authRequestInit } from "./authz";
import type { CanvasDocument, LoginSession } from "./types";

export class CanvasDraftRequestError extends Error {
  readonly repairable: boolean;
  readonly terminalGeneration: boolean;

  constructor(message: string, terminalGeneration: boolean, repairable = false) {
    super(message);
    this.name = "CanvasDraftRequestError";
    this.terminalGeneration = terminalGeneration;
    this.repairable = repairable;
  }
}

export async function draftLectureCanvas(
  courseId: string,
  lectureId: string,
  session: LoginSession,
): Promise<CanvasDocument> {
  return requestLectureCanvas(courseId, lectureId, session, "draft");
}

export async function repairLectureCanvas(
  courseId: string,
  lectureId: string,
  session: LoginSession,
): Promise<CanvasDocument> {
  return requestLectureCanvas(courseId, lectureId, session, "repair");
}

async function requestLectureCanvas(
  courseId: string,
  lectureId: string,
  session: LoginSession,
  action: "draft" | "repair",
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
    );
  }
  let canvas: CanvasDocument;
  try {
    canvas =
      response.status === 202
        ? await pollCanvasGeneration(courseId, lectureId, session, requestKey)
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

async function pollCanvasGeneration(
  courseId: string,
  lectureId: string,
  session: LoginSession,
  requestKey: string,
): Promise<CanvasDocument> {
  while (true) {
    await new Promise((resolve) => window.setTimeout(resolve, 1500));
    const response = await fetch(
      apiUrl(`/admin/courses/${courseId}/lectures/${lectureId}/canvas/draft/status`),
      authRequestInit(session, { headers: { "Idempotency-Key": requestKey } }),
    );
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
      );
    }
    if (status?.status === "completed" && status.canvas) return status.canvas;
    if (status?.status !== "running") {
      throw new CanvasDraftRequestError("Invalid canvas generation status.", false);
    }
  }
}

function canvasGenerationStorageKey(
  courseId: string,
  lectureId: string,
  action: "draft" | "repair",
) {
  return `lecturepilot:canvas-generation:${courseId}:${lectureId}:${action}`;
}
