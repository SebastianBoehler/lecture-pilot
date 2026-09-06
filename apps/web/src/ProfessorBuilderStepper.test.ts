import { describe, expect, it } from "vitest";

import { builderSteps } from "./ProfessorBuilderStepper";

describe("professor builder source-routing gate", () => {
  it("allows approved teaching designs to proceed without optional media review", () => {
    const steps = builderSteps({
      bundleReady: true,
      canvasReady: false,
      courseReady: true,
      designReady: true,
      draftReviewed: false,
      reviewAvailable: true,
      reviewReady: false,
      routingReady: true,
      workspacePublished: false,
    });
    expect(steps.find((step) => step.id === "generate")?.available).toBe(true);
    expect(steps.find((step) => step.id === "publish")?.available).toBe(false);
  });

  it("keeps media and generation locked until current routing is confirmed", () => {
    const locked = builderSteps({
      bundleReady: true,
      canvasReady: false,
      courseReady: true,
      designReady: false,
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
      "design",
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
      designReady: false,
      draftReviewed: false,
      reviewAvailable: true,
      reviewReady: false,
      routingReady: true,
      workspacePublished: false,
    });
    expect(confirmed.find((step) => step.id === "review")?.available).toBe(true);
  });
});
