import { describe, expect, it } from "vitest";

import { buildLearningTree } from "./learningTree";

describe("buildLearningTree", () => {
  it("creates ordered branches from prerequisite relationships", () => {
    const tree = buildLearningTree([
      { id: "foundation", prerequisites: [] },
      { id: "left", prerequisites: ["foundation"] },
      { id: "right", prerequisites: ["foundation"] },
      { id: "leaf", prerequisites: ["left", "right"] },
    ]);

    expect(tree.map((branch) => branch.node.id)).toEqual(["foundation"]);
    expect(tree[0]?.children.map((branch) => branch.node.id)).toEqual(["left", "right"]);
    expect(tree[0]?.children[0]?.children[0]?.node.id).toBe("leaf");
  });

  it("keeps cyclic or missing prerequisite nodes visible as roots", () => {
    const tree = buildLearningTree([
      { id: "first", prerequisites: ["second"] },
      { id: "second", prerequisites: ["first"] },
      { id: "orphan", prerequisites: ["missing"] },
    ]);

    expect(tree.map((branch) => branch.node.id)).toEqual(["second", "orphan"]);
    expect(tree[0]?.children[0]?.node.id).toBe("first");
  });
});
