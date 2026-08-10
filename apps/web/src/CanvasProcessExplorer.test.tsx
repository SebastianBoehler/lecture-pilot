import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { ComponentBlock } from "./CanvasInteractiveComponents";
import { renderWithI18n } from "./test/renderWithI18n";

it("replaces a filename caption and balances a five-step process", () => {
  renderWithI18n(
    <ComponentBlock
      block={{
        id: "llm-history",
        type: "component",
        component_id: "llm-history-process",
        component_type: "process_explorer",
        component_ref: "llm-history-process.yaml",
        caption: "llm-history-process.yaml",
        items: [],
        component_data: {
          chart_type: null,
          x_label: null,
          y_label: null,
          control_label: null,
          labels: [],
          frames: [],
          steps: Array.from({ length: 5 }, (_, index) => ({
            title: `Stage ${index + 1}`,
            text: `Explanation ${index + 1}`,
          })),
        },
      }}
      className="canvas-block"
      sourceMarker={null}
      onSubmitAnswer={vi.fn()}
    />,
  );

  expect(screen.getByRole("heading", { name: "LLM history" })).toBeVisible();
  expect(screen.queryByText("llm-history-process.yaml")).not.toBeInTheDocument();
  expect(screen.getByRole("list")).toHaveClass("is-five-step");
});

it("renders LaTeX throughout a generated process", () => {
  const { container } = renderWithI18n(
    <ComponentBlock
      block={{
        id: "ridge-derivation",
        type: "component",
        component_type: "process_explorer",
        caption: "Ridge regression derivation",
        text: "Follow the objective \\(L(w)\\) through each step.",
        items: [],
        component_data: {
          chart_type: null,
          x_label: null,
          y_label: null,
          control_label: null,
          labels: [],
          frames: [],
          steps: [
            {
              title: "Add \\(\\lambda I\\)",
              text: "Obtain \\(\\left(\\Phi^{\\top}\\Phi + \\lambda I\\right)w = \\Phi^{\\top}Y\\).",
            },
            { title: "Solve", text: "Isolate \\(w\\)." },
          ],
        },
      }}
      className="canvas-block"
      sourceMarker={null}
      onSubmitAnswer={vi.fn()}
    />,
  );

  expect(container.querySelector(".canvas-component-header .katex")).not.toBeNull();
  expect(container.querySelector(".canvas-process-step-title .katex")).not.toBeNull();
  expect(container.querySelector(".canvas-process-detail h4 .katex")).not.toBeNull();
  expect(container.querySelector(".canvas-process-detail p .katex")).not.toBeNull();
});
