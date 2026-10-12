import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LearnerOnboarding } from "./LearnerOnboarding";
import { renderWithI18n } from "../test/renderWithI18n";

describe("LearnerOnboarding", () => {
  it("collects a goal, explains calibration, and returns to the multi-course dashboard", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn().mockResolvedValue(undefined);
    renderWithI18n(<LearnerOnboarding onComplete={onComplete} />);

    expect(screen.getByText(/step 1 of 2/i)).toBeInTheDocument();
    expect(screen.queryByText(/quick setup/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/learning style/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /understand concepts deeply/i }));

    expect(screen.getByText(/step 2 of 2/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /continue/i })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /calibrates from your work/i })).toBeInTheDocument();
    expect(screen.getByText(/answers, quizzes, and checkpoints/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /start lecture/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /go to dashboard/i }));

    expect(onComplete).toHaveBeenCalledWith("understand_deeply");
  });

  it("stays open as a modal dialog until a goal is chosen", () => {
    renderWithI18n(<LearnerOnboarding onComplete={vi.fn()} />);
    const dialog = screen.getByRole("dialog", { name: /what are you working toward/i });
    expect(dialog).toHaveAttribute("open");

    const cancel = new Event("cancel", { cancelable: true });
    fireEvent(dialog, cancel);

    expect(cancel.defaultPrevented).toBe(true);
    expect(dialog).toHaveAttribute("open");
  });
});
