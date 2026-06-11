import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ComponentBlock } from "./CanvasInteractiveComponents";
import type { CanvasBlock } from "./types";

describe("CanvasInteractiveComponents", () => {
  it("renders single-choice quiz components through the prefab registry", async () => {
    const user = userEvent.setup();
    const onSubmitAnswer = vi.fn();
    const block: CanvasBlock = {
      id: "risk-threshold-check",
      type: "component",
      component_id: "risk-threshold-check",
      component_type: "single_choice_quiz",
      component_ref: "risk-threshold-check.yaml",
      component_version: 2,
      caption: "Risk threshold component",
      text: "Which action should minimize cost-sensitive risk?",
      items: ["Choose the lowest expected risk", "Always choose the highest posterior"],
      option_ids: ["lowest-risk", "highest-posterior"],
      answer_index: 0,
    };

    render(
      <ComponentBlock
        block={block}
        className="canvas-block"
        sourceMarker={<span>source marker</span>}
        onSubmitAnswer={onSubmitAnswer}
      />,
    );

    expect(screen.getByText("Risk threshold component")).toBeInTheDocument();
    expect(screen.queryByText("source marker")).not.toBeInTheDocument();
    const correct = screen.getByRole("button", { name: /A Choose the lowest expected risk/i });
    await user.click(correct);

    expect(onSubmitAnswer).toHaveBeenCalledWith(block, "Choose the lowest expected risk", 0);
    expect(correct).toHaveClass("is-correct");
  });

  it("renders unsupported component definitions without executing course code", () => {
    render(
      <ComponentBlock
        block={{
          id: "custom-3d",
          type: "component",
          component_id: "custom-3d",
          component_type: "custom_react_component",
          caption: "Custom 3D widget",
          items: [],
        }}
        className="canvas-block"
        sourceMarker={null}
        onSubmitAnswer={vi.fn()}
      />,
    );

    expect(screen.getByText("Custom 3D widget")).toBeInTheDocument();
    expect(screen.getByText("custom_react_component")).toBeInTheDocument();
  });
});
