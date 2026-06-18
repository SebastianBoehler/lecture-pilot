import type { CanvasDocument } from "./types";

const CANVAS_DRAFT_CONCURRENCY = 3;

export async function generateLectureCanvasDrafts({
  draft,
  lectureIds,
}: {
  draft: (lectureId: string) => Promise<CanvasDocument>;
  lectureIds: string[];
}) {
  const canvases = new Array<CanvasDocument>(lectureIds.length);
  let nextIndex = 0;
  const workerCount = Math.min(CANVAS_DRAFT_CONCURRENCY, lectureIds.length);
  const workers = Array.from({ length: workerCount }, async () => {
    while (nextIndex < lectureIds.length) {
      const currentIndex = nextIndex;
      nextIndex += 1;
      canvases[currentIndex] = await draft(lectureIds[currentIndex]);
    }
  });
  await Promise.all(workers);
  return canvases;
}
