import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { builderSteps, ProfessorBuilderStepper } from "./ProfessorBuilderStepper";
import { renderWithI18n } from "./test/renderWithI18n";

describe("five-stage course creation", () => {
  it.each(["upload", "sources", "review"] as const)(
    "gives %s its own appropriate stage without requiring a video",
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
        "03 Media",
        "04 Learning plan",
        "05 Review & publish",
      ]);
      expect(buttons[activeStep === "review" ? 2 : 1]).toHaveAttribute("aria-current", "step");
      expect(buttons[4]).toBeEnabled();
      fireEvent.click(buttons[4]);
      expect(onStepChange).toHaveBeenCalledWith("generate");
    },
  );
});
