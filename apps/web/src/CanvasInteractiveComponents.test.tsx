import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ComponentBlock } from "./CanvasInteractiveComponents";
import { renderWithI18n } from "./test/renderWithI18n";
import type { CanvasBlock } from "./types";

describe("CanvasInteractiveComponents", () => {
  it("renders unsupported component definitions without executing course code", () => {
    renderWithI18n(
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

  it("renders an exact chart and updates it from the generated frame control", () => {
    const block: CanvasBlock = {
      id: "risk-cost-explorer",
      type: "component",
      component_id: "risk-cost-explorer",
      component_type: "interactive_chart",
      component_ref: "risk-cost-explorer.yaml",
      component_version: 1,
      caption: "Cost-sensitive risk",
      text: "Predict which action will minimize risk, then move the control.",
      items: [],
      component_data: {
        chart_type: "bar",
        x_label: "Action",
        y_label: "Expected risk",
        control_label: "False-negative cost",
        labels: ["Reject", "Classify"],
        frames: [
          {
            label: "1x",
            values: [0.2, 0.6],
            explanation: "Reject has lower expected risk.",
          },
          {
            label: "5x",
            values: [0.8, 0.3],
            explanation: "Classify now has lower expected risk.",
          },
        ],
        steps: [],
      },
    };

    renderWithI18n(
      <ComponentBlock
        block={block}
        className="canvas-block"
        sourceMarker={<span>lecture source</span>}
        onSubmitAnswer={vi.fn()}
      />,
    );

    expect(screen.getByRole("img", { name: /Cost-sensitive risk at 1x/i })).toBeVisible();
    expect(screen.getByRole("slider", { name: "False-negative cost" })).toHaveValue("0");
    expect(screen.getByText("Reject has lower expected risk.")).toBeVisible();
    fireEvent.click(screen.getByText("View exact data"));
    expect(screen.getByRole("cell", { name: "0.2" })).toBeVisible();

    fireEvent.change(screen.getByRole("slider", { name: "False-negative cost" }), {
      target: { value: "1" },
    });

    expect(screen.getByRole("img", { name: /Cost-sensitive risk at 5x/i })).toBeVisible();
    expect(screen.getByText("Classify now has lower expected risk.")).toBeVisible();
    expect(screen.getByRole("cell", { name: "0.8" })).toBeVisible();
    expect(screen.getByText("lecture source")).toBeVisible();
  });

  it("renders scatter points and their exact coordinates", () => {
    renderWithI18n(
      <ComponentBlock
        block={{
          id: "class-clusters",
          type: "component",
          component_type: "interactive_chart",
          caption: "Class clusters",
          items: [],
          component_data: {
            chart_type: "scatter",
            x_label: "Feature one",
            y_label: "Feature two",
            control_label: null,
            labels: [],
            row_labels: [],
            frames: [
              {
                label: "Observed samples",
                values: [],
                points: [
                  { label: "Sample A", x: 1, y: 2, series: "Class A" },
                  { label: "Sample B", x: 3, y: 4, series: "Class B" },
                ],
                matrix: [],
                explanation: "The samples form two visible groups.",
              },
            ],
            steps: [],
          },
        }}
        className="canvas-block"
        sourceMarker={null}
        onSubmitAnswer={vi.fn()}
      />,
    );

    expect(screen.getByRole("img", { name: /Class clusters at Observed samples/i })).toBeVisible();
    fireEvent.click(screen.getByText("View exact data"));
    expect(screen.getByRole("row", { name: "Sample A Class A 1 2" })).toBeVisible();
  });

  it("renders a heatmap with an accessible matrix", () => {
    renderWithI18n(
      <ComponentBlock
        block={{
          id: "confusion-heatmap",
          type: "component",
          component_type: "interactive_chart",
          caption: "Prediction errors",
          items: [],
          component_data: {
            chart_type: "heatmap",
            x_label: "Predicted class",
            y_label: "Actual class",
            control_label: null,
            labels: ["Predicted A", "Predicted B"],
            row_labels: ["Actual A", "Actual B"],
            frames: [
              {
                label: "Validation set",
                values: [],
                points: [],
                matrix: [
                  [8, 2],
                  [1, 9],
                ],
                explanation: "Most predictions lie on the diagonal.",
              },
            ],
            steps: [],
          },
        }}
        className="canvas-block"
        sourceMarker={null}
        onSubmitAnswer={vi.fn()}
      />,
    );

    expect(screen.getByRole("img", { name: /Prediction errors at Validation set/i })).toBeVisible();
    fireEvent.click(screen.getByText("View exact data"));
    expect(screen.getByRole("row", { name: "Actual A 8 2" })).toBeVisible();
  });

  it("lets the learner inspect each stage of a generated process", async () => {
    const user = userEvent.setup();
    const block: CanvasBlock = {
      id: "bayes-process",
      type: "component",
      component_id: "bayes-process",
      component_type: "process_explorer",
      component_ref: "bayes-process.yaml",
      component_version: 1,
      caption: "Bayesian decision process",
      text: "Select each stage and explain what information changes.",
      items: [],
      component_data: {
        chart_type: null,
        x_label: null,
        y_label: null,
        control_label: null,
        labels: [],
        frames: [],
        steps: [
          { title: "Start with the prior", text: "Represent belief before observing evidence." },
          { title: "Apply the likelihood", text: "Measure compatibility with each class." },
          { title: "Choose by risk", text: "Combine posterior belief with decision costs." },
        ],
      },
    };

    renderWithI18n(
      <ComponentBlock
        block={block}
        className="canvas-block"
        sourceMarker={null}
        onSubmitAnswer={vi.fn()}
      />,
    );

    expect(screen.queryByText("Interactive process")).not.toBeInTheDocument();
    expect(screen.getByText("Represent belief before observing evidence.")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Previous step" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Next step" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /2 Apply the likelihood/i }));
    expect(screen.getByText("Measure compatibility with each class.")).toBeVisible();
    expect(screen.getByText("Step 2 of 3")).toBeVisible();
  });

  it("localizes the trusted component chrome", () => {
    renderWithI18n(
      <ComponentBlock
        block={{
          id: "bayes-process",
          type: "component",
          component_type: "process_explorer",
          caption: "Bayes-Ablauf",
          items: [],
          component_data: {
            chart_type: null,
            x_label: null,
            y_label: null,
            control_label: null,
            labels: [],
            frames: [],
            steps: [
              { title: "Prior", text: "Vorwissen darstellen." },
              { title: "Likelihood", text: "Evidenz berücksichtigen." },
            ],
          },
        }}
        className="canvas-block"
        sourceMarker={null}
        onSubmitAnswer={vi.fn()}
      />,
      { locale: "de" },
    );

    expect(screen.queryByText("Interaktiver Ablauf")).not.toBeInTheDocument();
    expect(screen.getByText("Schritt 1 von 2")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Nächster Schritt" })).not.toBeInTheDocument();
  });
});
