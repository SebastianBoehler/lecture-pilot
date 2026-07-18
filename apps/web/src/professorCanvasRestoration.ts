import { CanvasDraftLoadError, getDraftLectureCanvas } from "./api";
import type { CanvasGenerationProgress } from "./professorCanvasGeneration";
import type { CanvasDocument, LoginSession } from "./types";

type RestoredCanvas = {
  canvas: CanvasDocument;
  lectureId: string;
};

export async function restoreFullCourseCanvasDrafts({
  courseId,
  lectureIds,
  session,
}: {
  courseId: string;
  lectureIds: string[];
  session: LoginSession;
}) {
  const restored: RestoredCanvas[] = [];
  const progress = await Promise.all(
    lectureIds.map(async (lectureId): Promise<CanvasGenerationProgress> => {
      try {
        const canvas = await getDraftLectureCanvas(courseId, lectureId, session);
        restored.push({ canvas, lectureId });
        return { lectureId, status: "ready" };
      } catch (error) {
        return restorationFailure(lectureId, error);
      }
    }),
  );
  const restoredByLecture = new Map(restored.map((item) => [item.lectureId, item]));
  return {
    restored: lectureIds.flatMap((lectureId) => {
      const item = restoredByLecture.get(lectureId);
      return item ? [item] : [];
    }),
    progress,
  };
}

function restorationFailure(lectureId: string, error: unknown): CanvasGenerationProgress {
  const message = error instanceof Error ? error.message : "Canvas draft could not be restored.";
  if (error instanceof TypeError) {
    return { errorKind: "network", lectureId, message, status: "error" };
  }
  const errorKind =
    error instanceof CanvasDraftLoadError && error.repairable ? "repair" : "service";
  return { errorKind, lectureId, message, status: "error" };
}
