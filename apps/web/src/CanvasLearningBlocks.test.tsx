import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CheckpointBlock, QuizBlock, TableBlock } from "./CanvasLearningBlocks";
import type { CanvasBlock } from "./types";

describe("CanvasLearningBlocks", () => {
  it("renders checkpoint, quiz, and markdown table blocks", () => {
    const checkpoint = block("checkpoint", {
      caption: "Risk gate",
      text: "Explain why \\lambda_{ik} changes the decision.",
    });
    const quiz = block("quiz", {
      caption: "Retrieval check",
      items: ["Prior", "Loss term"],
      text: "Which term changes the threshold?",
      answer_index: 1,
    });
    const table = block("table", {
      text: "| Action | Risk |\n| --- | --- |\n| Reject | Lower harm |",
    });

    render(
      <>
        <CheckpointBlock block={checkpoint} className="canvas-block" highlightedText={null} sourceMarker={null} />
        <QuizBlock block={quiz} className="canvas-block" highlightedText={null} sourceMarker={null} />
        <TableBlock block={table} className="canvas-block" highlightedText={null} sourceMarker={null} />
      </>,
    );

    expect(screen.getByText("Risk gate")).toBeInTheDocument();
    expect(screen.getByText("Retrieval check")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "A Prior" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Action" })).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("\\lambda");
  });

  it("emits selected quiz options", async () => {
    const user = userEvent.setup();
    const onSubmitAnswer = vi.fn();
    const quiz = block("quiz", {
      caption: "Retrieval check",
      items: ["Prior", "Expected risk"],
      text: "What should be minimized?",
      answer_index: 1,
    });

    render(
      <QuizBlock
        block={quiz}
        className="canvas-block"
        highlightedText={null}
        sourceMarker={null}
        onSubmitAnswer={onSubmitAnswer}
      />,
    );

    const correct = screen.getByRole("button", { name: "B Expected risk" });
    await user.click(correct);

    expect(onSubmitAnswer).toHaveBeenCalledWith(quiz, "Expected risk", 1);
    expect(correct).toHaveClass("is-correct");
  });

  it("marks incorrect quiz selections and still reveals the correct option", async () => {
    const user = userEvent.setup();
    const quiz = block("quiz", {
      items: ["Posterior only", "Expected risk"],
      text: "What should be minimized?",
      answer_index: 1,
    });

    render(<QuizBlock block={quiz} className="canvas-block" highlightedText={null} sourceMarker={null} />);

    const wrong = screen.getByRole("button", { name: "A Posterior only" });
    const correct = screen.getByRole("button", { name: "B Expected risk" });
    await user.click(wrong);

    expect(wrong).toHaveClass("is-incorrect");
    expect(correct).toHaveClass("is-correct");
  });
});

function block(type: CanvasBlock["type"], overrides: Partial<CanvasBlock>): CanvasBlock {
  return {
    asset_path: null,
    asset_url: null,
    caption: null,
    id: `${type}-block`,
    items: [],
    text: null,
    type,
    ...overrides,
  };
}
