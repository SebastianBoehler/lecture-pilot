/**
 * The course builder's resume/retry state machine: one pure reducer owns the active step and
 * every piece of generation state that resuming or retrying touches.
 */
import { retryStartsFresh } from "./canvasDraftApi";
import type { BuilderStep } from "./ProfessorBuilderStepper";
import type { CanvasGenerationProgress } from "./professorCanvasGeneration";
import type { CanvasDocument } from "../shared/types";

export type BuilderFlowState = Readonly<{
  activeStep: BuilderStep;
  mediaReviewed: boolean;
  draftReviewed: boolean;
  canvas: CanvasDocument | null;
  generatedIds: readonly string[];
  progress: readonly CanvasGenerationProgress[];
  warnings: readonly string[];
  retryingIds: readonly string[];
  /** Lectures whose server-side generation was running when the builder resumed. */
  restoredGeneratingIds: readonly string[];
  /** Bumps when drafts are restored, so reviews reload without reacting to sibling retries. */
  draftRestoreRevision: number;
}>;

/** What the backend reported when a saved setup was resumed. */
export type RestoreSnapshot =
  | { kind: "no-uploads" }
  | { kind: "routing-unavailable" }
  | {
      kind: "full-course";
      routingConfirmed: boolean;
      activeLectureId: string;
      restored: readonly { lectureId: string; canvas: CanvasDocument }[];
      progress: readonly CanvasGenerationProgress[];
    }
  | {
      kind: "single-lecture";
      routingConfirmed: boolean;
      lectureId: string;
      canvas: CanvasDocument | null;
    };

export type BuilderFlowEvent =
  | { type: "navigate"; step: BuilderStep }
  | { type: "canvas-reset" }
  | { type: "routing-confirmed" }
  | { type: "media-continued" }
  | { type: "media-changed" }
  | { type: "draft-review-continued" }
  | { type: "restore-finished"; snapshot: RestoreSnapshot }
  | {
      type: "generation-queued";
      lectureIds: readonly string[];
      targetIds: readonly string[];
      clearWarnings: boolean;
    }
  | { type: "background-generation-started"; lectureIds: readonly string[] }
  | { type: "background-generation-rejected"; lectureIds: readonly string[] }
  | { type: "requests-dispatched"; lectureIds: readonly string[] }
  | { type: "progress"; item: CanvasGenerationProgress }
  | { type: "draft-ready"; lectureId: string; canvas: CanvasDocument }
  | { type: "generation-finished"; lectureIds: readonly string[]; canvas: CanvasDocument | null }
  | { type: "retry-started"; lectureId: string }
  | { type: "retry-settled"; lectureId: string }
  | { type: "restored-generation-settled"; lectureId: string };

export function initialBuilderFlow(activeStep: BuilderStep): BuilderFlowState {
  return { activeStep, ...emptyGeneration(), mediaReviewed: false, draftRestoreRevision: 0 };
}

function emptyGeneration() {
  return {
    draftReviewed: false,
    canvas: null,
    generatedIds: [],
    progress: [],
    warnings: [],
    retryingIds: [],
    restoredGeneratingIds: [],
  };
}

export function builderFlowReducer(
  state: BuilderFlowState,
  event: BuilderFlowEvent,
): BuilderFlowState {
  switch (event.type) {
    case "navigate":
      return { ...state, activeStep: event.step };
    case "canvas-reset":
      return { ...state, ...emptyGeneration(), mediaReviewed: false };
    case "routing-confirmed":
      return { ...state, ...emptyGeneration(), mediaReviewed: false, activeStep: "media" };
    case "media-continued":
      return { ...state, mediaReviewed: true, activeStep: "design" };
    case "media-changed":
      // Selected videos change the drafts: earlier drafts are no longer current.
      return {
        ...state,
        mediaReviewed: true,
        canvas: null,
        generatedIds: [],
        progress: [],
        warnings: [],
      };
    case "draft-review-continued":
      return { ...state, draftReviewed: true, activeStep: "publish" };
    case "restore-finished":
      return restored(state, event.snapshot);
    case "generation-queued": {
      const queued = new Set(event.lectureIds);
      return {
        ...state,
        draftReviewed: false,
        // Finished lectures stay ready; only the queued ones run again.
        progress: event.targetIds.map((lectureId) => ({
          lectureId,
          status: queued.has(lectureId) ? "pending" : "ready",
        })),
        warnings: event.clearWarnings ? [] : state.warnings,
      };
    }
    case "background-generation-started": {
      const ids = new Set(event.lectureIds);
      return {
        ...state,
        progress: [
          ...state.progress.filter((item) => !ids.has(item.lectureId)),
          ...event.lectureIds.map((lectureId) => ({ lectureId, status: "generating" as const })),
        ],
      };
    }
    case "background-generation-rejected":
      return {
        ...state,
        progress: state.progress.filter((i) => !event.lectureIds.includes(i.lectureId)),
      };
    case "requests-dispatched":
      return {
        ...state,
        restoredGeneratingIds: state.restoredGeneratingIds.filter(
          (id) => !event.lectureIds.includes(id),
        ),
      };
    case "progress":
      return {
        ...state,
        progress: state.progress.map((item) =>
          item.lectureId === event.item.lectureId
            ? {
                ...item,
                ...event.item,
                errorKind: event.item.errorKind,
                message: event.item.message,
              }
            : item,
        ),
      };
    case "draft-ready":
      return {
        ...state,
        canvas: event.canvas,
        generatedIds: union(state.generatedIds, [event.lectureId]),
        warnings: union(state.warnings, event.canvas.warnings ?? []),
      };
    case "generation-finished":
      return {
        ...state,
        canvas: event.canvas,
        generatedIds: union(state.generatedIds, event.lectureIds),
      };
    case "retry-started":
      return { ...state, retryingIds: union(state.retryingIds, [event.lectureId]) };
    case "retry-settled":
      return { ...state, retryingIds: state.retryingIds.filter((id) => id !== event.lectureId) };
    case "restored-generation-settled":
      return {
        ...state,
        restoredGeneratingIds: state.restoredGeneratingIds.filter((id) => id !== event.lectureId),
      };
  }
}

function restored(state: BuilderFlowState, snapshot: RestoreSnapshot): BuilderFlowState {
  if (snapshot.kind === "no-uploads") return { ...state, activeStep: "upload" };
  if (snapshot.kind === "routing-unavailable") return { ...state, activeStep: "sources" };
  const planStep = (base: BuilderFlowState): BuilderFlowState =>
    // Media is optional; a resumed setup with confirmed sources continues with the plan.
    snapshot.routingConfirmed
      ? { ...base, mediaReviewed: true, activeStep: "design" }
      : { ...base, activeStep: "sources" };
  if (snapshot.kind === "single-lecture") {
    if (!snapshot.canvas) return planStep(state);
    return {
      ...state,
      canvas: snapshot.canvas,
      generatedIds: [snapshot.lectureId],
      warnings: snapshot.canvas.warnings ?? [],
      draftReviewed: false,
      draftRestoreRevision: state.draftRestoreRevision + 1,
      activeStep: "generate",
    };
  }
  const active =
    snapshot.restored.find((item) => item.lectureId === snapshot.activeLectureId) ??
    snapshot.restored[0];
  const next: BuilderFlowState = {
    ...state,
    canvas: active?.canvas ?? null,
    generatedIds: snapshot.restored.map((item) => item.lectureId),
    progress: snapshot.progress,
    restoredGeneratingIds: snapshot.progress
      .filter((item) => item.status === "generating")
      .map((item) => item.lectureId),
    warnings: union(
      [],
      snapshot.restored.flatMap((item) => item.canvas.warnings ?? []),
    ),
    draftReviewed: false,
    draftRestoreRevision: state.draftRestoreRevision + 1,
  };
  // Any started draft (ready, running or failed) means the next action lives in review.
  const draftingStarted = snapshot.progress.some((item) => item.status !== "pending");
  return draftingStarted ? { ...next, activeStep: "generate" } : planStep(next);
}

/** Which lectures one "Generate" press drafts, which of them repair, and which start fresh. */
export function planGeneration(state: BuilderFlowState, readyIds: readonly string[]) {
  const failed = (id: string) =>
    state.progress.some((item) => item.lectureId === id && item.status === "error");
  const unfinished = readyIds.filter((id) => !state.generatedIds.includes(id) || failed(id));
  const lectureIds = unfinished.length ? unfinished : [...readyIds];
  return {
    lectureIds,
    repairIds: new Set(
      state.progress
        .filter((item) => lectureIds.includes(item.lectureId) && item.errorKind === "repair")
        .map((item) => item.lectureId),
    ),
    /** Regenerating every finished lecture starts with fresh warnings. */
    clearWarnings: unfinished.length === 0,
  };
}

/** A retry after a failed attempt is a new request; an interrupted one resumes under its key. */
export function freshRequestIds(state: BuilderFlowState, lectureIds: readonly string[]) {
  return state.progress
    .filter(
      (item) =>
        item.status === "error" && retryStartsFresh(item) && lectureIds.includes(item.lectureId),
    )
    .map((item) => item.lectureId);
}

function union<T>(current: readonly T[], added: readonly T[]): T[] {
  return Array.from(new Set([...current, ...added]));
}
