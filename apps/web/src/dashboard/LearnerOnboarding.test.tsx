import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LearnerOnboarding } from "./LearnerOnboarding";
import { renderWithI18n } from "../test/renderWithI18n";

describe("LearnerOnboarding", () => {
  it("collects a goal, background, and topics before saving the profile", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn().mockResolvedValue(undefined);
    renderWithI18n(<LearnerOnboarding onComplete={onComplete} />);

    expect(screen.getByText("Step 1 of 3")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /understand concepts deeply/i }));
    expect(screen.getByText("Step 2 of 3")).toBeInTheDocument();
    await user.type(screen.getByRole("textbox", { name: "Your background" }), "I know Python.");
    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(screen.getByText("Step 3 of 3")).toBeInTheDocument();
    await user.type(screen.getByRole("textbox", { name: "Topics for examples" }), "Robotics");
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByRole("textbox", { name: "Your background" })).toHaveValue("I know Python.");
    await user.click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.getByText(/share these details with its AI provider/i)).toBeInTheDocument();
    expect(onComplete).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Save and go to dashboard" }));

    expect(onComplete).toHaveBeenCalledExactlyOnceWith("understand_deeply", {
      background: "I know Python.",
      exampleInterests: "Robotics",
      complete: true,
    });
  });

  it("skips setup without saving draft answers", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn().mockResolvedValue(undefined);
    renderWithI18n(<LearnerOnboarding onComplete={onComplete} />);

    await user.click(screen.getByRole("button", { name: /keep up with lectures/i }));
    await user.type(screen.getByRole("textbox", { name: "Your background" }), "Draft");
    await user.click(screen.getByRole("button", { name: "Skip setup" }));

    expect(onComplete).toHaveBeenCalledExactlyOnceWith(null, { complete: true });
  });

  it("treats Escape as skipping setup", () => {
    const onComplete = vi.fn().mockReturnValue(new Promise<void>(() => {}));
    renderWithI18n(<LearnerOnboarding onComplete={onComplete} />);
    const dialog = screen.getByRole("dialog", { name: /what are you working toward/i });
    expect(dialog).toHaveAttribute("open");

    const cancel = new Event("cancel", { cancelable: true });
    fireEvent(dialog, cancel);

    expect(cancel.defaultPrevented).toBe(true);
    expect(onComplete).toHaveBeenCalledExactlyOnceWith(null, { complete: true });
  });
});
