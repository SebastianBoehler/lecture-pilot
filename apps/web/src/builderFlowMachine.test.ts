import { describe, expect, it } from "vitest";

import {
  builderFlowReducer,
  freshRequestIds,
  initialBuilderFlow,
  planGeneration,
  type BuilderFlowEvent,
  type BuilderFlowState,
} from "./builderFlowMachine";
import type { CanvasDocument } from "./types";

const canvas = (lectureId: string, warnings: string[] = []) =>
  ({ id: lectureId, course_id: "c", lecture_id: lectureId, warnings }) as unknown as CanvasDocument;

function run(...events: BuilderFlowEvent[]): BuilderFlowState {
  return events.reduce(builderFlowReducer, initialBuilderFlow("define"));
}

const fullCourse = (
  progress: BuilderFlowState["progress"],
  restoredIds: string[] = [],
  routingConfirmed = true,
): BuilderFlowEvent => ({
  type: "restore-finished",
  snapshot: {
    kind: "full-course",
    routingConfirmed,
    activeLectureId: "l2",
    restored: restoredIds.map((lectureId) => ({ lectureId, canvas: canvas(lectureId) })),
    progress,
  },
});

describe("builder resume (70621aa, 8ccfe85)", () => {
  it("resumes at uploads, sources or the learning plan from the backend state", () => {
    expect(run({ type: "restore-finished", snapshot: { kind: "no-uploads" } }).activeStep).toBe(
      "upload",
    );
    // An unproposed or unreadable routing returns to the source review.
    const routing = run({ type: "restore-finished", snapshot: { kind: "routing-unavailable" } });
    expect(routing.activeStep).toBe("sources");
    expect(run(fullCourse([], [], false)).activeStep).toBe("sources");
    // Media is optional: confirmed sources continue with the learning plan.
    const plan = run(fullCourse([{ lectureId: "l1", status: "pending" }]));
    expect(plan).toMatchObject({ activeStep: "design", mediaReviewed: true });
  });

  it.each(["ready", "generating", "error"] as const)(
    "resumes at review once any draft was started (%s)",
    (status) => {
      const state = run(
        fullCourse([
          { lectureId: "l1", status },
          { lectureId: "l2", status: "pending" },
        ]),
      );
      expect(state.activeStep).toBe("generate");
    },
  );

  it("keeps polling running drafts and selects the active lecture's restored canvas", () => {
    const state = run(
      fullCourse(
        [
          { lectureId: "l1", status: "ready" },
          { lectureId: "l2", status: "ready" },
          { lectureId: "l3", status: "generating" },
        ],
        ["l1", "l2"],
      ),
    );
    expect(state.restoredGeneratingIds).toEqual(["l3"]);
    expect(state.canvas?.lecture_id).toBe("l2");
    expect(state.generatedIds).toEqual(["l1", "l2"]);
    expect(state.draftRestoreRevision).toBe(1);
    const settled = builderFlowReducer(state, {
      type: "restored-generation-settled",
      lectureId: "l3",
    });
    expect(settled.restoredGeneratingIds).toEqual([]);
  });

  it("resumes a single lecture at review only when its draft exists", () => {
    const found = run({
      type: "restore-finished",
      snapshot: {
        kind: "single-lecture",
        routingConfirmed: true,
        lectureId: "l1",
        canvas: canvas("l1", ["w"]),
      },
    });
    expect(found).toMatchObject({ activeStep: "generate", generatedIds: ["l1"], warnings: ["w"] });
    const missing = run({
      type: "restore-finished",
      snapshot: { kind: "single-lecture", routingConfirmed: true, lectureId: "l1", canvas: null },
    });
    expect(missing).toMatchObject({ activeStep: "design", canvas: null });
  });
});

describe("builder retry (b840613, b5ba5c7, 0557c78, 6d37663)", () => {
  const afterRun = run(
    {
      type: "generation-queued",
      lectureIds: ["l1", "l2"],
      targetIds: ["l1", "l2"],
      clearWarnings: true,
    },
    { type: "draft-ready", lectureId: "l1", canvas: canvas("l1", ["kept"]) },
    { type: "progress", item: { lectureId: "l1", status: "ready" } },
    {
      type: "progress",
      item: { lectureId: "l2", status: "error", errorKind: "repair", message: "x" },
    },
  );

  it("drafts only unfinished lectures again, repairing a repairable failure", () => {
    const plan = planGeneration(afterRun, ["l1", "l2"]);
    expect(plan.lectureIds).toEqual(["l2"]);
    expect([...plan.repairIds]).toEqual(["l2"]);
    expect(plan.clearWarnings).toBe(false);
    const queued = builderFlowReducer(afterRun, {
      type: "generation-queued",
      lectureIds: plan.lectureIds,
      targetIds: ["l1", "l2"],
      clearWarnings: plan.clearWarnings,
    });
    // Completed drafts stay ready while the failed lecture runs again.
    expect(queued.progress).toEqual([
      { lectureId: "l1", status: "ready" },
      { lectureId: "l2", status: "pending" },
    ]);
    expect(queued.warnings).toEqual(["kept"]);
  });

  it("treats a failed regenerated lecture as unfinished even after an earlier draft", () => {
    const regenerated = builderFlowReducer(
      { ...afterRun, generatedIds: ["l1", "l2"] },
      { type: "progress", item: { lectureId: "l2", status: "error", errorKind: "service" } },
    );
    expect(planGeneration(regenerated, ["l1", "l2"]).lectureIds).toEqual(["l2"]);
    const all = { ...regenerated, progress: [] };
    expect(planGeneration(all, ["l1", "l2"])).toMatchObject({
      lectureIds: ["l1", "l2"],
      clearWarnings: true,
    });
  });

  it("clears an error's kind and message when a retry reports progress", () => {
    const retried = builderFlowReducer(afterRun, {
      type: "progress",
      item: { lectureId: "l2", status: "generating" },
    });
    expect(retried.progress[1]).toEqual({
      lectureId: "l2",
      status: "generating",
      errorKind: undefined,
      message: undefined,
    });
  });

  it("starts a failed retry as a fresh request but resumes interrupted ones", () => {
    const state = {
      ...afterRun,
      progress: [
        { lectureId: "l1", status: "error" as const, errorKind: "interrupted" as const },
        { lectureId: "l2", status: "error" as const, errorKind: "repair" as const },
        { lectureId: "l3", status: "error" as const, errorKind: "network" as const },
      ],
    };
    expect(freshRequestIds(state, ["l1", "l2", "l3"])).toEqual(["l2"]);
  });

  it("removes a rejected background start without touching other lectures", () => {
    const started = builderFlowReducer(afterRun, {
      type: "background-generation-started",
      lectureIds: ["l3"],
    });
    expect(started.progress.at(-1)).toEqual({ lectureId: "l3", status: "generating" });
    const rejected = builderFlowReducer(started, {
      type: "background-generation-rejected",
      lectureIds: ["l3"],
    });
    expect(rejected.progress).toEqual(afterRun.progress);
  });
});

describe("sibling retries keep completed reviews (104db18)", () => {
  it("does not change the restored canvas or review revision while another lecture retries", () => {
    const restored = run(
      fullCourse(
        [
          { lectureId: "l1", status: "ready" },
          { lectureId: "l2", status: "error" },
        ],
        ["l1"],
      ),
    );
    const retrying = [
      { type: "retry-started", lectureId: "l2" },
      { type: "requests-dispatched", lectureIds: ["l2"] },
      { type: "progress", item: { lectureId: "l2", status: "generating" } },
    ] as BuilderFlowEvent[];
    const next = retrying.reduce(builderFlowReducer, restored);
    expect(next.retryingIds).toEqual(["l2"]);
    expect(next.draftRestoreRevision).toBe(restored.draftRestoreRevision);
    expect(next.canvas).toBe(restored.canvas);
    expect(
      builderFlowReducer(next, { type: "retry-settled", lectureId: "l2" }).retryingIds,
    ).toEqual([]);
  });
});

describe("stage transitions", () => {
  it("routes source confirmation to media and media to the learning plan (b9da26b)", () => {
    const confirmed = run(
      { type: "draft-ready", lectureId: "l1", canvas: canvas("l1") },
      { type: "routing-confirmed" },
    );
    expect(confirmed).toMatchObject({ activeStep: "media", canvas: null, mediaReviewed: false });
    expect(builderFlowReducer(confirmed, { type: "media-continued" })).toMatchObject({
      activeStep: "design",
      mediaReviewed: true,
    });
  });

  it("invalidates drafts when selected media change", () => {
    const changed = run(
      { type: "draft-ready", lectureId: "l1", canvas: canvas("l1", ["w"]) },
      { type: "media-changed" },
    );
    expect(changed).toMatchObject({
      canvas: null,
      generatedIds: [],
      warnings: [],
      mediaReviewed: true,
    });
  });
});
