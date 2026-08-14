import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { ComponentBlock } from "./CanvasInteractiveComponents";
import { renderWithI18n } from "./test/renderWithI18n";

const emptyComponentData = {
  chart_type: null,
  control_type: null,
  control_label: null,
  labels: [],
  row_labels: [],
  frames: [],
  steps: [],
};

it("keeps links in visual data as non-navigable text", () => {
  renderWithI18n(
    <ComponentBlock
      block={{
        id: "linked-flow",
        type: "component",
        component_type: "visual_artifact",
        component_version: 1,
        caption: "Linked visual",
        items: [],
        component_data: {
          ...emptyComponentData,
          x_label: null,
          y_label: null,
          visual_layout: "flow",
          visual_nodes: [
            { id: "a", label: "A", detail: "[External](https://evil.invalid)", value: null },
            { id: "b", label: "B", detail: "Safe text", value: null },
          ],
          visual_edges: [{ from_id: "a", to_id: "b", label: null }],
          visual_series: [],
          visual_annotations: [],
        },
      }}
      className="canvas-block"
      sourceMarker={null}
      onSubmitAnswer={vi.fn()}
    />,
  );

  expect(screen.getByText("External")).toBeVisible();
  expect(screen.queryByRole("link", { name: "External" })).not.toBeInTheDocument();
});

it.each([
  [-1e308, 1e308],
  [Number.MIN_VALUE, Number.MIN_VALUE],
])("keeps SVG geometry finite for the plot range %s to %s", (low, high) => {
  const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
  try {
    const { container } = renderWithI18n(
      <ComponentBlock
        block={{
          id: "extreme-plot",
          type: "component",
          component_type: "visual_artifact",
          component_version: 1,
          caption: "Extreme finite plot",
          items: [],
          component_data: {
            ...emptyComponentData,
            x_label: "x",
            y_label: "y",
            visual_layout: "plot",
            visual_nodes: [],
            visual_edges: [],
            visual_series: [
              {
                label: "Extreme",
                mark: "line",
                points: [
                  { label: "Low", x: low, y: low, series: null },
                  { label: "High", x: high, y: high, series: null },
                ],
              },
            ],
            visual_annotations: [],
          },
        }}
        className="canvas-block"
        sourceMarker={null}
        onSubmitAnswer={vi.fn()}
      />,
    );

    const geometry = Array.from(container.querySelectorAll("polyline, circle"))
      .flatMap((element) => ["points", "cx", "cy"].map((name) => element.getAttribute(name)))
      .filter(Boolean)
      .join(" ");
    expect(geometry).not.toContain("NaN");
    expect(consoleError).not.toHaveBeenCalled();
  } finally {
    consoleError.mockRestore();
  }
});
