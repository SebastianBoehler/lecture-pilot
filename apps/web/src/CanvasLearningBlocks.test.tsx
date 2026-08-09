import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { CheckpointBlock, QuizBlock, TableBlock } from "./CanvasLearningBlocks";
import { I18nProvider } from "./i18n";
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

    renderWithI18n(
      <>
        <CheckpointBlock
          block={checkpoint}
          className="canvas-block"
          highlightedText={null}
          sourceMarker={null}
        />
        <QuizBlock
          block={quiz}
          className="canvas-block"
          highlightedText={null}
          sourceMarker={null}
        />
        <TableBlock
          block={table}
          className="canvas-block"
          highlightedText={null}
          sourceMarker={null}
        />
      </>,
    );

    expect(screen.getByText("Risk gate")).toBeInTheDocument();
    expect(screen.getByText("Retrieval check")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "A Prior" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Action" })).toBeInTheDocument();
    expect(document.querySelector(".katex")).not.toBeNull();
  });

  it("restores a persisted accepted quiz attempt after reload", () => {
    const quiz = block("quiz", {
      items: ["Posterior only", "Expected risk"],
      text: "What should be minimized?",
    });

    renderWithI18n(
      <QuizBlock
        block={quiz}
        className="canvas-block"
        highlightedText={null}
        quizState={{
          selected_index: 0,
          correct: false,
          publication_version: 1,
          attempt_index: 1,
          first_attempt_correct: false,
          latest_outcome: "incorrect",
          correction_state: "needed",
        }}
        sourceMarker={null}
      />,
    );

    expect(screen.getByRole("button", { name: "A Posterior only" })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent(/not correct yet/i);
    expect(screen.getByRole("button", { name: /try a correction/i })).toBeInTheDocument();
  });

  it("submits an inline checkpoint answer from the main canvas", async () => {
    const user = userEvent.setup();
    const checkpoint = block("checkpoint", {
      caption: "Risk gate",
      text: "Explain how loss changes the decision.",
    });
    const onSubmitCheckpoint = vi.fn().mockResolvedValue(undefined);

    renderWithI18n(
      <CheckpointBlock
        block={checkpoint}
        className="canvas-block"
        highlightedText={null}
        sectionId="risk-section"
        sourceMarker={null}
        onSubmitCheckpoint={onSubmitCheckpoint}
      />,
    );

    await user.type(screen.getByLabelText(/your checkpoint answer/i), "Loss changes the risk.");
    await user.click(screen.getByRole("button", { name: /submit checkpoint answer/i }));

    expect(onSubmitCheckpoint).toHaveBeenCalledWith(
      "checkpoint-block",
      "risk-section",
      "Loss changes the risk.",
    );
    expect(await screen.findByRole("status")).toHaveTextContent(/feedback is available in chat/i);
  });

  it("keeps source markers and phrase highlights out of quiz cards", () => {
    const quiz = block("quiz", {
      items: ["Expected risk"],
      text: "Which answer captures expected risk?",
      answer_index: 0,
    });

    renderWithI18n(
      <QuizBlock
        block={quiz}
        className="canvas-block"
        highlightedText="expected risk"
        sourceMarker={<span>source marker</span>}
      />,
    );

    expect(screen.queryByText("source marker")).not.toBeInTheDocument();
    expect(document.querySelector(".phrase-highlight")).toBeNull();
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

function renderWithI18n(node: ReactNode) {
  return render(
    <I18nProvider locale="en" setLocale={vi.fn()}>
      {node}
    </I18nProvider>,
  );
}
