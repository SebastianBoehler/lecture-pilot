import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { builderSteps, ProfessorBuilderStepper } from "./ProfessorBuilderStepper";
import { renderWithI18n } from "./test/renderWithI18n";

describe("four-stage course creation", () => {
  it.each(["upload", "sources", "review"] as const)(
    "keeps %s inside Materials and makes optional media unnecessary for review",
    (activeStep) => {
      const onStepChange = vi.fn();
      renderWithI18n(
        <ProfessorBuilderStepper
          activeStep={activeStep}
          onStepChange={onStepChange}
          steps={builderSteps({
            courseReady: true,
            bundleReady: true,
            reviewAvailable: true,
            routingReady: true,
            designReady: true,
            reviewReady: false,
            canvasReady: false,
            draftReviewed: false,
            workspacePublished: false,
          })}
        />,
      );
      const buttons = within(screen.getByRole("navigation")).getAllByRole("button");
      expect(buttons.map((button) => button.getAttribute("aria-label"))).toEqual([
        "01 Course",
        "02 Materials",
        "03 Learning plan",
        "04 Review & publish",
      ]);
      expect(buttons[1]).toHaveAttribute("aria-current", "step");
      expect(buttons[3]).toBeEnabled();
      fireEvent.click(buttons[3]);
      expect(onStepChange).toHaveBeenCalledWith("generate");
    },
  );
});
