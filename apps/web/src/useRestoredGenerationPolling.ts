import { useEffect, useEffectEvent } from "react";

import type { CanvasGenerationProgress } from "./professorCanvasGeneration";
import { restoreFullCourseCanvasDrafts } from "./professorCanvasRestoration";
import type { CanvasDocument, LoginSession } from "./types";

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
    let inFlight = false;
    let active = true;
    const timer = window.setInterval(() => {
      if (inFlight) return;
      inFlight = true;
      void poll(key.split("|"), () => active)
        .catch((error: unknown) => {
          if (active) {
            reportError(
              error instanceof Error ? error.message : "Could not load current draft status.",
            );
          }
        })
        .finally(() => {
          inFlight = false;
        });
    }, intervalMs);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [courseId, intervalMs, key]);
}
