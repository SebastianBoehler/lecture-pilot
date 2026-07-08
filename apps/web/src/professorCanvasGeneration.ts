import type { CanvasDocument } from "./types";

const CANVAS_DRAFT_CONCURRENCY = 5;

export type CanvasGenerationStatus = "pending" | "generating" | "ready" | "error";

export type CanvasGenerationProgress = {
  lectureId: string;
  status: CanvasGenerationStatus;
  message?: string;
};

export async function generateLectureCanvasDrafts({
  draft,
  lectureIds,
  onProgress,
}: {
  draft: (lectureId: string) => Promise<CanvasDocument>;
  lectureIds: string[];
  onProgress?: (progress: CanvasGenerationProgress) => void;
}) {
  const canvases = new Array<CanvasDocument>(lectureIds.length);
  let nextIndex = 0;
  const workerCount = Math.min(CANVAS_DRAFT_CONCURRENCY, lectureIds.length);
  const workers = Array.from({ length: workerCount }, async () => {
    while (nextIndex < lectureIds.length) {
      const currentIndex = nextIndex;
      nextIndex += 1;
      const lectureId = lectureIds[currentIndex];
      onProgress?.({ lectureId, status: "generating" });
      try {
        canvases[currentIndex] = await draft(lectureId);
        onProgress?.({ lectureId, status: "ready" });
      } catch (error) {
        onProgress?.({
          lectureId,
          status: "error",
          message: error instanceof Error ? error.message : "Canvas generation failed.",
        });
        throw error;
      }
    }
  });
  await Promise.all(workers);
  return canvases;
}
