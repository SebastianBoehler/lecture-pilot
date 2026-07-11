import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LearnerOnboarding } from "./LearnerOnboarding";
import { renderWithI18n } from "./test/renderWithI18n";

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
});
