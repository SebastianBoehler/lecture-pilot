import { describe, expect, it } from "vitest";

import { builderSteps } from "./ProfessorBuilderStepper";

describe("professor builder source-routing gate", () => {
  it("keeps media and generation locked until current routing is confirmed", () => {
    const locked = builderSteps({
      bundleReady: true,
      canvasReady: false,
      courseReady: true,
      draftReviewed: false,
      reviewAvailable: true,
      reviewReady: false,
      routingReady: false,
      workspacePublished: false,
    });

    expect(locked.map((step) => step.id)).toEqual([
      "define",
      "upload",
      "sources",
      "review",
      "generate",
      "publish",
    ]);
    expect(locked.find((step) => step.id === "sources")?.available).toBe(true);
    expect(locked.find((step) => step.id === "review")?.available).toBe(false);
    expect(locked.find((step) => step.id === "generate")?.available).toBe(false);

    const confirmed = builderSteps({
      bundleReady: true,
      canvasReady: false,
      courseReady: true,
      draftReviewed: false,
      reviewAvailable: true,
      reviewReady: false,
      routingReady: true,
      workspacePublished: false,
    });
    expect(confirmed.find((step) => step.id === "review")?.available).toBe(true);
  });
});
