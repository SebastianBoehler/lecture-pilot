import { useEffect, useEffectEvent, useState, type Dispatch } from "react";

import { getCourseLectures, getDraftLectureCanvas } from "./api";
import type { BuilderFlowEvent } from "./builderFlowMachine";
import { listCourseWorkspaces, getSourceBundle, SourceRoutingRequestError } from "./professorApi";
import { restoreFullCourseCanvasDrafts } from "./professorCanvasRestoration";
import {
  writeSavedFlow,
  type CourseSetup,
  type CourseWorkspaceState,
  type SavedProfessorFlow,
} from "./professorBuilderState";
import type { lectureFromWorkspace } from "./professorWorkspaceView";
import type { CourseSourceRoutingManifest, LoginSession, SourceBundleManifest } from "./types";

const UNPROPOSED = "Generate an agent source-assignment proposal before reviewing it.";

export type RestoredWorkspace = {
  bundle: SourceBundleManifest;
  lectures: ReturnType<typeof lectureFromWorkspace>[];
  publishedLectureIds: string[];
};

/**
 * Resumes a saved setup and keeps it saved: reads what the backend holds and hands it to the
 * flow machine, which decides where the builder resumes.
 */
export function useBuilderRestore({
  savedFlow,
  current,
  session,
  setup,
  dispatch,
  loadRouting,
  onRestored,
  onWorkspaceMissing,
  setError,
}: {
  savedFlow: SavedProfessorFlow;
  /** The flow to keep saved once the saved one has been restored. */
  current: SavedProfessorFlow;
  session: LoginSession;
  setup: CourseSetup;
  dispatch: Dispatch<BuilderFlowEvent>;
  loadRouting: (courseId: string) => Promise<CourseSourceRoutingManifest>;
  onRestored: (courseId: string, restored: Partial<RestoredWorkspace>) => void;
  onWorkspaceMissing: () => void;
  setError: (message: string | null) => void;
}) {
  const [isRestoring, setIsRestoring] = useState(false);
  const [restored, setRestored] = useState(!savedFlow.bundleReady && !savedFlow.canvasReady);
  const restoreSaved = useEffectEvent(() =>
    restore(savedFlow.workspace, {
      quietDraftMiss: !savedFlow.canvasReady,
      skipWhenMissing: true,
    }),
  );
  const persisted = JSON.stringify(current);

  useEffect(() => {
    let cancelled = false;
    if (!restored)
      void restoreSaved().then(() => {
        if (!cancelled) setRestored(true);
      });
    return () => {
      cancelled = true;
    };
  }, [restored]);

  useEffect(() => {
    if (restored) writeSavedFlow(JSON.parse(persisted) as SavedProfessorFlow);
  }, [persisted, restored]);

  async function restore(
    target: CourseWorkspaceState | null,
    options: { quietDraftMiss?: boolean; skipWhenMissing?: boolean } = {},
  ) {
    if (!target) {
      if (!options.skipWhenMissing) setError("Create a course workspace before refreshing state.");
      return;
    }
    setIsRestoring(true);
    setError(null);
    try {
      const own = (await listCourseWorkspaces(session)).find(
        (item) => item.course.id === target.courseId,
      );
      onRestored(target.courseId, { publishedLectureIds: own?.publishedLectureIds ?? [] });
      if (options.skipWhenMissing && !own) {
        onWorkspaceMissing();
        return;
      }
      const bundle = await getSourceBundle(target.courseId, session);
      onRestored(target.courseId, { bundle });
      const lectures = await getCourseLectures(target.courseId, session);
      onRestored(target.courseId, { lectures });
      if (!bundle.files.length) {
        dispatch({ type: "restore-finished", snapshot: { kind: "no-uploads" } });
        return;
      }
      let routing: CourseSourceRoutingManifest;
      try {
        routing = await loadRouting(target.courseId);
      } catch (routingError) {
        const unproposed =
          routingError instanceof SourceRoutingRequestError &&
          routingError.status === 409 &&
          routingError.message === UNPROPOSED;
        dispatch({ type: "restore-finished", snapshot: { kind: "routing-unavailable" } });
        setError(
          unproposed
            ? null
            : routingError instanceof Error
              ? routingError.message
              : "Source assignments failed to load.",
        );
        return;
      }
      if (setup.target === "full-course") {
        const drafts = await restoreFullCourseCanvasDrafts({
          courseId: target.courseId,
          lectureIds: lectures.map((lecture) => lecture.id),
          session,
        });
        dispatch({
          type: "restore-finished",
          snapshot: {
            kind: "full-course",
            routingConfirmed: routing.confirmed,
            activeLectureId: target.lectureId,
            restored: drafts.restored,
            progress: drafts.progress,
          },
        });
        return;
      }
      let canvas = null;
      try {
        canvas = await getDraftLectureCanvas(target.courseId, target.lectureId, session);
      } catch (canvasError) {
        if (!options.quietDraftMiss) {
          setError(
            canvasError instanceof Error
              ? canvasError.message
              : "Could not restore professor preview.",
          );
        }
      }
      dispatch({
        type: "restore-finished",
        snapshot: {
          kind: "single-lecture",
          routingConfirmed: routing.confirmed,
          lectureId: target.lectureId,
          canvas,
        },
      });
    } catch (restoreError) {
      if (!options.skipWhenMissing) {
        setError(
          restoreError instanceof Error
            ? restoreError.message
            : "Could not refresh workspace state.",
        );
      }
    } finally {
      setIsRestoring(false);
    }
  }

  return { isRestoring, restore };
}
