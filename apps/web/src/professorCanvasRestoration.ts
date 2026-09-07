import { runBoundedTasks } from "./boundedTaskPool";
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
  const progress: CanvasGenerationProgress[] = [];
  await runBoundedTasks(lectureIds, 4, async (lectureId, index) => {
    try {
      const canvas = await getDraftLectureCanvas(courseId, lectureId, session);
      restored.push({ canvas, lectureId });
      progress[index] = { lectureId, status: "ready" };
    } catch (error) {
      progress[index] = restorationFailure(lectureId, error);
    }
  });
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
  if (error instanceof CanvasDraftLoadError && error.generationStatus === "running") {
    return { lectureId, status: "generating" };
  }
  if (
    error instanceof CanvasDraftLoadError &&
    error.status === 404 &&
    !error.repairable &&
    error.generationStatus === null
  ) {
    return { lectureId, status: "pending" };
  }
  if (error instanceof TypeError) {
    throw new Error(
      "Could not load current draft status. Refresh workspace state to reconnect; saved drafts and running jobs are unchanged.",
    );
  }
  const errorKind =
    error instanceof CanvasDraftLoadError && error.repairable ? "repair" : "service";
  return { errorKind, lectureId, message, status: "error" };
}
