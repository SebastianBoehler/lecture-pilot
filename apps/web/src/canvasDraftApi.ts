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
      headers: { "Idempotency-Key": requestKey },
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
  if (window.sessionStorage.getItem(storageKey) === requestKey) {
    window.sessionStorage.removeItem(storageKey);
  }
  return payload as CanvasDocument;
}

function canvasGenerationStorageKey(
  courseId: string,
  lectureId: string,
  action: "draft" | "repair",
) {
  return `lecturepilot:canvas-generation:${courseId}:${lectureId}:${action}`;
}
