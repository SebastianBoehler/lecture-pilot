import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { InteractiveChart } from "./CanvasInteractiveChart";
import { renderWithI18n } from "./test/renderWithI18n";
import type { CanvasBlock } from "./types";

describe("InteractiveChart", () => {
  it("uses explicit buttons for a discrete two-state comparison", async () => {
    const user = userEvent.setup();
    const block: CanvasBlock = {
      id: "class-separation",
      type: "component",
      component_type: "interactive_chart",
      caption: "Class separation",
      items: [],
      component_data: {
        chart_type: "scatter",
        x_label: "Feature one",
        y_label: "Feature two",
        control_label: "Representation",
        control_type: "buttons",
        labels: [],
        frames: [
          {
            label: "Raw features",
            values: [],
            points: [
              { label: "Sample A", x: 1, y: 1, series: "Class A" },
              { label: "Sample B", x: 2, y: 2, series: "Class B" },
            ],
            explanation: "The classes overlap.",
          },
          {
            label: "Learned features",
            values: [],
            points: [
              { label: "Sample A", x: 1, y: 1, series: "Class A" },
              { label: "Sample B", x: 4, y: 4, series: "Class B" },
            ],
            explanation: "The classes separate.",
          },
        ],
        steps: [],
      },
    };

    renderWithI18n(<InteractiveChart block={block} className="canvas-block" sourceMarker={null} />);

    expect(screen.queryByRole("slider")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Raw features" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    await user.click(screen.getByRole("button", { name: "Learned features" }));

    expect(screen.getByRole("button", { name: "Learned features" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(
      screen.getByRole("img", { name: /Class separation at Learned features/i }),
    ).toBeVisible();
    expect(screen.getByText("The classes separate.")).toBeVisible();
  });
});
