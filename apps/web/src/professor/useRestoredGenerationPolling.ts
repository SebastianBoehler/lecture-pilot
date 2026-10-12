import { useEffect, useEffectEvent } from "react";

import { pollUntil, PollTimeoutError } from "../shared/polling";
import type { CanvasGenerationProgress } from "./professorCanvasGeneration";
import { restoreFullCourseCanvasDrafts } from "./professorCanvasRestoration";
import type { CanvasDocument, LoginSession } from "../shared/types";

const RESTORED_POLL_TIMEOUT_MS = 2 * 60 * 60 * 1000;

/** Follows jobs that were already running when the builder was restored (e.g. after reload). */
export function useRestoredGenerationPolling({
  courseId,
  lectureIds,
  session,
  intervalMs = 15_000,
  onDraftReady,
  onProgress,
  onSettled,
  onError,
}: {
  courseId: string | null;
  lectureIds: readonly string[];
  session: LoginSession;
  intervalMs?: number;
  onDraftReady: (lectureId: string, canvas: CanvasDocument) => void;
  onProgress: (progress: CanvasGenerationProgress) => void;
  onSettled: (lectureId: string) => void;
  onError: (message: string) => void;
}) {
  const key = lectureIds.join("|");
  const reportError = useEffectEvent(onError);
  const poll = useEffectEvent(async (ids: string[], isCurrent: () => boolean) => {
    if (!courseId) return;
    const result = await restoreFullCourseCanvasDrafts({ courseId, lectureIds: ids, session });
    if (!isCurrent()) return;
    for (const item of result.restored) onDraftReady(item.lectureId, item.canvas);
    for (const item of result.progress) {
      onProgress(item);
      if (item.status !== "generating") onSettled(item.lectureId);
    }
  });
  useEffect(() => {
    if (!courseId || !key) return;
    const controller = new AbortController();
    pollUntil({
      initialDelayMs: intervalMs,
      maxDelayMs: intervalMs * 2,
      timeoutMs: RESTORED_POLL_TIMEOUT_MS,
      signal: controller.signal,
      poll: async (signal) => {
        try {
          await poll(key.split("|"), () => !signal?.aborted);
        } catch (error) {
          if (!signal?.aborted) {
            reportError(
              error instanceof Error ? error.message : "Could not load current draft status.",
            );
          }
        }
        return { done: false };
      },
    }).catch((error: unknown) => {
      if (error instanceof PollTimeoutError) {
        reportError("Generation is still running on the server. Reload to keep following it.");
      }
    });
    return () => controller.abort();
  }, [courseId, intervalMs, key]);
}
