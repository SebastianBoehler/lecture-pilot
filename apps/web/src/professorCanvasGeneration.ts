import type { CanvasDocument } from "./types";
import { CanvasDraftRequestError } from "./canvasDraftApi";

const CANVAS_DRAFT_CONCURRENCY = 3;
const CANVAS_DRAFT_RETRY_DELAYS_MS = [1500, 3500];
const CANVAS_DRAFT_WORKER_STAGGER_MS = 400;

export type CanvasGenerationStatus = "pending" | "generating" | "ready" | "error";
export type CanvasGenerationErrorKind = "network" | "service";

export type CanvasGenerationProgress = {
  lectureId: string;
  status: CanvasGenerationStatus;
  errorKind?: CanvasGenerationErrorKind;
  message?: string;
};

export class CanvasGenerationBatchError extends Error {
  readonly failures: CanvasGenerationProgress[];

  constructor(failures: CanvasGenerationProgress[]) {
    super("One or more lecture canvas drafts failed.");
    this.name = "CanvasGenerationBatchError";
    this.failures = failures;
  }
}

const wait = (delayMs: number) =>
  new Promise((resolve) => {
    window.setTimeout(resolve, delayMs);
  });

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Canvas generation failed.";
}

export function describeCanvasGenerationError(error: unknown): {
  errorKind: CanvasGenerationErrorKind;
  message?: string;
} {
  const message = errorMessage(error);
  const isNetworkFailure =
    error instanceof TypeError &&
    (/failed to fetch/i.test(message) ||
      /network ?error/i.test(message) ||
      /load failed/i.test(message));
  return isNetworkFailure ? { errorKind: "network" } : { errorKind: "service", message };
}

function shouldRetryCanvasDraft(error: unknown) {
  if (error instanceof CanvasDraftRequestError && error.terminalGeneration) return false;
  const message = errorMessage(error).toLowerCase();
  return (
    (error instanceof TypeError &&
      (message.includes("failed to fetch") ||
        message.includes("network error") ||
        message.includes("load failed"))) ||
    message.includes("rate") ||
    message.includes("429") ||
    message.includes("502") ||
    message.includes("503") ||
    message.includes("bad gateway") ||
    message.includes("still in progress") ||
    message.includes("service unavailable") ||
    message.includes("model request failed")
  );
}

async function draftWithRetry(
  lectureId: string,
  draft: (lectureId: string) => Promise<CanvasDocument>,
  onProgress?: (progress: CanvasGenerationProgress) => void,
) {
  for (let attempt = 0; attempt <= CANVAS_DRAFT_RETRY_DELAYS_MS.length; attempt += 1) {
    try {
      return await draft(lectureId);
    } catch (error) {
      const retryDelayMs = CANVAS_DRAFT_RETRY_DELAYS_MS[attempt];
      if (retryDelayMs === undefined || !shouldRetryCanvasDraft(error)) throw error;
      onProgress?.({
        lectureId,
        status: "generating",
        message: `Provider busy; retrying in ${Math.round(retryDelayMs / 1000)}s.`,
      });
      await wait(retryDelayMs);
    }
  }
  throw new Error("Canvas generation failed.");
}

export async function generateLectureCanvasDrafts({
  draft,
  lectureIds,
  onDraftReady,
  onProgress,
}: {
  draft: (lectureId: string) => Promise<CanvasDocument>;
  lectureIds: string[];
  onDraftReady?: (lectureId: string, canvas: CanvasDocument) => void;
  onProgress?: (progress: CanvasGenerationProgress) => void;
}) {
  const canvases = new Array<CanvasDocument>(lectureIds.length);
  const failures: CanvasGenerationProgress[] = [];
  let nextIndex = 0;
  const workerCount = Math.min(CANVAS_DRAFT_CONCURRENCY, lectureIds.length);
  const workers = Array.from({ length: workerCount }, async (_, workerIndex) => {
    if (workerIndex > 0) await wait(workerIndex * CANVAS_DRAFT_WORKER_STAGGER_MS);
    while (nextIndex < lectureIds.length) {
      const currentIndex = nextIndex;
      nextIndex += 1;
      const lectureId = lectureIds[currentIndex];
      onProgress?.({ lectureId, status: "generating" });
      try {
        canvases[currentIndex] = await draftWithRetry(lectureId, draft, onProgress);
        onDraftReady?.(lectureId, canvases[currentIndex]);
        onProgress?.({ lectureId, status: "ready" });
      } catch (error) {
        const failure = {
          lectureId,
          status: "error",
          ...describeCanvasGenerationError(error),
        } satisfies CanvasGenerationProgress;
        failures.push(failure);
        onProgress?.(failure);
      }
    }
  });
  await Promise.all(workers);
  if (failures.length > 0) {
    throw new CanvasGenerationBatchError(failures);
  }
  return canvases;
}
