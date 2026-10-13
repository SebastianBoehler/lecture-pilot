import { describe, expect, it } from "vitest";

import { diffGoals } from "./goalDiff";

const goal = (id: string, title: string, outcome = `${title} outcome`) => ({ id, title, outcome });

describe("diffGoals", () => {
  it("classifies kept, changed, added and removed goals in the new order", () => {
    const previous = [
      goal("g1", "Gradient descent"),
      goal("g2", "Learning rate"),
      goal("g3", "Momentum"),
    ];
    const current = [
      goal("g1", "Gradient descent"),
      goal("g2", "Learning rate", "Choose a stable learning rate"),
      goal("g9", "Line search"),
    ];
    expect(
      diffGoals(previous, current).map(({ kind, before, after }) => [kind, before?.id, after?.id]),
    ).toEqual([
      ["kept", "g1", "g1"],
      ["changed", "g2", "g2"],
      ["added", undefined, "g9"],
      ["removed", "g3", undefined],
    ]);
  });

  it("matches regenerated goals with new ids by title or outcome", () => {
    const previous = [goal("old-1", "Convexity"), goal("old-2", "Saddle points", "Spot saddles")];
    const current = [
      goal("new-1", " convexity "),
      goal("new-2", "Saddle point geometry", "Spot saddles"),
    ];
    expect(diffGoals(previous, current).map(({ kind }) => kind)).toEqual(["kept", "changed"]);
  });

  it("matches every previous goal at most once", () => {
    const previous = [goal("a", "Same")];
    const current = [goal("b", "Same"), goal("c", "Same")];
    expect(diffGoals(previous, current).map(({ kind }) => kind)).toEqual(["kept", "added"]);
  });
});
