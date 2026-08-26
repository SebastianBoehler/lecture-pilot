import { describe, expect, it } from "vitest";

import { builderSteps } from "./ProfessorBuilderStepper";

describe("practice-design builder blocking", () => {
  it("places learning plans between sources and media and blocks generation until every plan is approved", () => {
    const blocked = builderSteps({
      bundleReady: true,
      canvasReady: false,
      courseReady: true,
      designReady: false,
      draftReviewed: false,
      reviewAvailable: true,
      reviewReady: true,
      routingReady: true,
      workspacePublished: false,
    });
    const ready = builderSteps({
      ...Object.fromEntries(blocked.map((step) => [step.id, step.ready])),
      bundleReady: true,
      canvasReady: false,
      courseReady: true,
      designReady: true,
      draftReviewed: false,
      reviewAvailable: true,
      reviewReady: true,
      routingReady: true,
      workspacePublished: false,
    });

    expect(blocked.map((step) => step.id)).toEqual([
      "define",
      "upload",
      "sources",
      "design",
      "review",
      "generate",
      "publish",
    ]);
    expect(blocked.find((step) => step.id === "review")?.available).toBe(true);
    expect(blocked.find((step) => step.id === "generate")?.available).toBe(false);
    expect(ready.find((step) => step.id === "generate")?.available).toBe(true);
  });
});
