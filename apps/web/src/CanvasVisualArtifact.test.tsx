import { fireEvent, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { ComponentBlock } from "./CanvasInteractiveComponents";
import { renderWithI18n } from "./test/renderWithI18n";

it("renders a composed flow as escaped data rather than generated markup", () => {
  const { container } = renderWithI18n(
    <ComponentBlock
      block={{
        id: "bayes-flow",
        type: "component",
        component_type: "visual_artifact",
        component_version: 1,
        caption: "Bayesian update",
        text: "Follow how evidence changes belief.",
        items: [],
        component_data: {
          chart_type: null,
          control_type: null,
          x_label: null,
          y_label: null,
          control_label: null,
          labels: [],
          row_labels: [],
          frames: [],
          steps: [],
          visual_layout: "flow",
          visual_nodes: [
            { id: "prior", label: "Prior", detail: "Initial belief", value: "40%" },
            {
              id: "evidence",
              label: "Evidence",
              detail: '<img src=x onerror="alert(1)">',
              value: null,
            },
            { id: "posterior", label: "Posterior", detail: "Updated belief", value: "75%" },
          ],
          visual_edges: [
            { from_id: "prior", to_id: "evidence", label: "combine" },
            { from_id: "evidence", to_id: "posterior", label: "normalize" },
          ],
          visual_series: [],
          visual_annotations: [
            { label: "The likelihood controls the update.", target_id: "evidence" },
          ],
        },
      }}
      className="canvas-block"
      sourceMarker={<span>lecture source</span>}
      onSubmitAnswer={vi.fn()}
    />,
  );

  expect(screen.getByRole("region", { name: "Bayesian update" })).toBeVisible();
  expect(screen.getByRole("list", { name: "Bayesian update" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Prior" })).toBeVisible();
  expect(screen.getByText("combine")).toBeVisible();
  expect(screen.getByText("The likelihood controls the update.")).toBeVisible();
  expect(screen.getByText('<img src=x onerror="alert(1)">')).toBeVisible();
  expect(container.querySelector("img")).toBeNull();
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  expect(screen.getByText("lecture source")).toBeVisible();
});

it("renders a plot with a complete accessible data equivalent", () => {
  renderWithI18n(
    <ComponentBlock
      block={{
        id: "training-plot",
        type: "component",
        component_type: "visual_artifact",
        component_version: 1,
        caption: "Training dynamics",
        text: "Compare the source-supported trajectories.",
        items: [],
        component_data: {
          chart_type: null,
          control_type: null,
          x_label: "Step",
          y_label: "Loss",
          control_label: null,
          labels: [],
          row_labels: [],
          frames: [],
          steps: [],
          visual_layout: "plot",
          visual_nodes: [],
          visual_edges: [],
          visual_series: [
            {
              label: "Method A",
              mark: "line",
              points: [
                { label: "Start", x: 0, y: 1, series: null },
                { label: "End", x: 1, y: 0.2, series: null },
              ],
            },
            {
              label: "Method B",
              mark: "point",
              points: [
                { label: "Start", x: 0, y: 0.8, series: null },
                { label: "End", x: 1, y: 0.3, series: null },
              ],
            },
          ],
          visual_annotations: [{ label: "Method A finishes lower.", target_id: null }],
        },
      }}
      className="canvas-block"
      sourceMarker={null}
      onSubmitAnswer={vi.fn()}
    />,
  );

  const plot = screen.getByRole("img", { name: "Training dynamics plot" });
  expect(plot).toHaveAccessibleDescription(
    "Method A — Start: Step 0, Loss 1; End: Step 1, Loss 0.2. Method B — Start: Step 0, Loss 0.8; End: Step 1, Loss 0.3.",
  );
  expect(screen.getByText("Method A finishes lower.")).toBeVisible();
  fireEvent.click(screen.getByText("View exact visual data"));
  expect(screen.getByRole("row", { name: "Method A Start 0 1" })).toBeVisible();
  expect(screen.getByRole("row", { name: "Method B End 1 0.3" })).toBeVisible();
});

it("fails closed when serialized plot data is invalid", () => {
  renderWithI18n(
    <ComponentBlock
      block={{
        id: "invalid-plot",
        type: "component",
        component_type: "visual_artifact",
        component_version: 1,
        caption: "Invalid visual",
        items: [],
        component_data: {
          chart_type: null,
          control_type: null,
          x_label: "Step",
          y_label: "Loss",
          control_label: null,
          labels: [],
          row_labels: [],
          frames: [],
          steps: [],
          visual_layout: "plot",
          visual_nodes: [],
          visual_edges: [],
          visual_series: [
            {
              label: "Broken",
              mark: "line",
              points: [
                { label: "Start", x: 0, y: null as unknown as number, series: null },
                { label: "End", x: 1, y: 0.2, series: null },
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

  expect(
    screen.getByText("This visual artifact contains invalid or incomplete data."),
  ).toBeVisible();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

it("fails closed instead of crashing on malformed serialized nodes", () => {
  renderWithI18n(
    <ComponentBlock
      block={{
        id: "invalid-flow",
        type: "component",
        component_type: "visual_artifact",
        component_version: 1,
        caption: "Invalid flow",
        items: [],
        component_data: {
          chart_type: null,
          control_type: null,
          x_label: null,
          y_label: null,
          control_label: null,
          labels: [],
          row_labels: [],
          frames: [],
          steps: [],
          visual_layout: "flow",
          visual_nodes: [
            null as never,
            { id: "valid", label: "Valid", detail: "Still not enough", value: null },
          ],
          visual_edges: [],
          visual_series: [],
          visual_annotations: [],
        },
      }}
      className="canvas-block"
      sourceMarker={null}
      onSubmitAnswer={vi.fn()}
    />,
  );

  expect(
    screen.getByText("This visual artifact contains invalid or incomplete data."),
  ).toBeVisible();
});
