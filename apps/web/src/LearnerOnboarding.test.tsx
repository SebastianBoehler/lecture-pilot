import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LearnerOnboarding } from "./LearnerOnboarding";
import { renderWithI18n } from "./test/renderWithI18n";
import type { Lecture } from "./types";

const lecture: Lecture = {
  id: "lecture-01",
  number: "01",
  title: "Foundations",
  date: "2026-04-01",
  attendance: "unknown",
};

describe("LearnerOnboarding", () => {
  it("collects a goal, explains evidence-driven calibration, and starts the next step", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn().mockResolvedValue(undefined);
    const onOpen = vi.fn();
    renderWithI18n(<LearnerOnboarding lecture={lecture} onComplete={onComplete} onOpen={onOpen} />);

    expect(screen.getByText(/step 1 of 2/i)).toBeInTheDocument();
    expect(screen.queryByText(/quick setup/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/learning style/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /understand concepts deeply/i }));

    expect(screen.getByText(/step 2 of 2/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /continue/i })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /calibrates from your work/i })).toBeInTheDocument();
    expect(screen.getByText(/answers, quizzes, and checkpoints/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /start lecture 01/i }));

    expect(onComplete).toHaveBeenCalledWith("understand_deeply");
    expect(onOpen).toHaveBeenCalledWith(lecture);
  });
});
