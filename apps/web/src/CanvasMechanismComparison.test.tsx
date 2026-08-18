import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { ComponentBlock } from "./CanvasInteractiveComponents";
import { renderWithI18n } from "./test/renderWithI18n";

it("shows generic mechanism alternatives and consequences on one shared scale", () => {
  const { container } = renderWithI18n(
    <ComponentBlock
      block={{
        id: "mechanism-comparison",
        type: "component",
        component_type: "mechanism_comparison",
        caption: "Compare two mechanisms",
        text: "Inspect how each mechanism changes the same downstream measures.",
        items: [],
        component_data: {
          chart_type: "line",
          control_type: null,
          x_label: "Input position",
          y_label: "Response",
          control_label: null,
          labels: ["Measure A", "Measure B"],
          row_labels: [],
          frames: [
            {
              label: "Approach one",
              values: [90, 85],
              points: [
                { label: "Start", x: 0, y: 0.9 },
                { label: "Middle", x: 1, y: 0.1 },
              ],
              matrix: [],
              explanation: "The first mechanism preserves the coupled behavior.",
            },
            {
              label: "Approach two",
              values: [110, 104],
              points: [
                { label: "Start", x: 0, y: 1 },
                { label: "Middle", x: 1, y: 0 },
              ],
              matrix: [],
              explanation: "The second mechanism changes the coupled outcome.",
            },
          ],
          steps: [],
        },
      }}
      className="canvas-block"
      sourceMarker={<span>lecture source</span>}
      onSubmitAnswer={vi.fn()}
    />,
  );

  expect(screen.getByRole("region", { name: "Compare two mechanisms" })).toBeVisible();
  expect(screen.queryByText("Mechanism comparison")).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Approach one" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Approach two" })).toBeVisible();
  expect(screen.getAllByRole("img", { name: /parameter profile/i })).toHaveLength(2);
  const profiles = Array.from(container.querySelectorAll(".canvas-mechanism-profile polyline"));
  expect(profiles[0]).not.toHaveAttribute("points", profiles[1].getAttribute("points"));
  expect(screen.getAllByText("Input position")).toHaveLength(2);
  expect(screen.getAllByText("Response")).toHaveLength(2);
  expect(screen.getByRole("row", { name: "Measure A 90 110" })).toBeVisible();
  expect(screen.getByText("The first mechanism preserves the coupled behavior.")).toBeVisible();
  expect(screen.getByText("The second mechanism changes the coupled outcome.")).toBeVisible();
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  expect(screen.getByText("lecture source")).toBeVisible();
});
