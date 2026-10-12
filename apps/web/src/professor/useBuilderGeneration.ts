import { useMemo, type Dispatch } from "react";

import {
  freshRequestIds,
  planGeneration,
  type BuilderFlowEvent,
  type BuilderFlowState,
} from "./builderFlowMachine";
import {
  draftLectureCanvas,
  forgetCanvasGenerationRequest,
  repairLectureCanvas,
} from "./canvasDraftApi";
import { useI18n } from "../i18n/i18n";
import {
  CanvasGenerationBatchError,
  generateLectureCanvasDrafts,
} from "./professorCanvasGeneration";
import type { useProfessorWorkflowRun } from "./professorWorkflowRun";
import { requireWorkspace } from "./professorWorkspaceView";
import type { CourseWorkspaceState } from "./professorBuilderState";
import type { LoginSession } from "../shared/types";
import { useRestoredGenerationPolling } from "./useRestoredGenerationPolling";
import { useUnmountSignal } from "../shared/useUnmountSignal";

/** Canvas drafting, background starts and per-lecture retries, driven by the flow machine. */
export function useBuilderGeneration({
  session,
  workspace,
  flow,
  dispatch,
  workflow,
  readyLectureIds,
  targetLectureIds,
  requireReady,
  canGenerate,
  allGoalsApproved,
  isFullCourse,
  previewLectures,
}: {
  session: LoginSession;
  workspace: CourseWorkspaceState | null;
  flow: BuilderFlowState;
  dispatch: Dispatch<BuilderFlowEvent>;
  workflow: ReturnType<typeof useProfessorWorkflowRun>;
  readyLectureIds: readonly string[];
  targetLectureIds: readonly string[];
  /** Confirms routing and goal approvals; `navigate` moves to the stage that needs work. */
  requireReady: (lectureIds: readonly string[], navigate: boolean) => Promise<void>;
  /** Sources, routing and at least one approved plan are in place. */
  canGenerate: boolean;
  allGoalsApproved: boolean;
  isFullCourse: boolean;
  previewLectures: { id: string; label: string; previewHref: string }[];
}) {
  const { t } = useI18n();
  const { run, setError, setNotice } = workflow;
  const retryingLectureIds = useMemo(() => new Set(flow.retryingIds), [flow.retryingIds]);
  // Status polling stops when the builder unmounts; the server-side jobs keep running.
  const generationSignal = useUnmountSignal();
  useRestoredGenerationPolling({
    courseId: workspace?.courseId ?? null,
    lectureIds: [...flow.restoredGeneratingIds],
    session,
    onDraftReady: (lectureId, canvas) => dispatch({ type: "draft-ready", lectureId, canvas }),
    onProgress: (item) => dispatch({ type: "progress", item }),
    onError: setError,
    onSettled: (lectureId) => dispatch({ type: "restored-generation-settled", lectureId }),
  });

  async function generate(
    courseId: string,
    lectureIds: string[],
    options: { repair?: boolean; repairIds?: ReadonlySet<string> } = {},
  ) {
    dispatch({ type: "requests-dispatched", lectureIds });
    for (const lectureId of freshRequestIds(flow, lectureIds)) {
      forgetCanvasGenerationRequest(courseId, lectureId);
    }
    try {
      return await generateLectureCanvasDrafts({
        lectureIds,
        draft: (lectureId) =>
          options.repair || options.repairIds?.has(lectureId)
            ? repairLectureCanvas(courseId, lectureId, session, generationSignal())
            : draftLectureCanvas(courseId, lectureId, session, generationSignal()),
        onDraftReady: (lectureId, canvas) => dispatch({ type: "draft-ready", lectureId, canvas }),
        onProgress: (item) => dispatch({ type: "progress", item }),
      });
    } catch (generationError) {
      if (generationError instanceof CanvasGenerationBatchError) return null;
      throw generationError;
    }
  }

  /** Start drafts for lectures whose goals are approved; other lectures keep their state. */
  async function startLectureGeneration(lectureIds: readonly string[]) {
    if (!workspace || !lectureIds.length) return;
    const ids = [...lectureIds];
    dispatch({ type: "background-generation-started", lectureIds: ids });
    try {
      // Background start: report problems without moving the professor away from their step.
      await requireReady(ids, false);
      if (!(await generate(workspace.courseId, ids))) return;
      setNotice(
        ids.length === 1
          ? t("builder.status.generatedOne")
          : t("builder.status.generatedMany", { count: ids.length }),
      );
    } catch (startError) {
      dispatch({ type: "background-generation-rejected", lectureIds: ids });
      setError(startError instanceof Error ? startError.message : "Canvas generation failed.");
    }
  }

  async function retry(lectureId: string) {
    if (flow.retryingIds.includes(lectureId)) return;
    dispatch({ type: "retry-started", lectureId });
    setError(null);
    try {
      const repair =
        flow.progress.find((item) => item.lectureId === lectureId)?.errorKind === "repair";
      await generate(requireWorkspace(workspace).courseId, [lectureId], { repair });
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : "Canvas retry failed.");
    } finally {
      dispatch({ type: "retry-settled", lectureId });
    }
  }

  return {
    canvas: flow.canvas,
    canGenerate: canGenerate && !retryingLectureIds.size,
    readyLectureIds,
    startLectureGeneration: (ids: readonly string[]) => void startLectureGeneration(ids),
    generationProgress: [...flow.progress],
    generatedCount: flow.generatedIds.length,
    generatedIds: [...flow.generatedIds],
    allGoalsApproved,
    isFullCourse,
    isGenerating:
      workflow.pendingAction === "generate" ||
      flow.progress.some((item) => item.status === "generating"),
    retryingLectureIds,
    onContinueToPublish: () => dispatch({ type: "draft-review-continued" }),
    previewLectures,
    totalCount: targetLectureIds.length,
    onRetry: (lectureId: string) => void retry(lectureId),
    onGenerate: () =>
      run("generate", async () => {
        const activeWorkspace = requireWorkspace(workspace);
        const ready = [...readyLectureIds];
        await requireReady(ready, true);
        const plan = planGeneration(flow, ready);
        dispatch({
          type: "generation-queued",
          lectureIds: plan.lectureIds,
          targetIds: targetLectureIds,
          clearWarnings: plan.clearWarnings,
        });
        const canvases = await generate(activeWorkspace.courseId, plan.lectureIds, {
          repairIds: plan.repairIds,
        });
        if (!canvases) return;
        dispatch({
          type: "generation-finished",
          lectureIds: plan.lectureIds,
          canvas: canvases[0] ?? null,
        });
        if (plan.lectureIds.length === 1) return t("builder.status.generatedOne");
        return t("builder.status.generatedMany", { count: plan.lectureIds.length });
      }),
  };
}
