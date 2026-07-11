import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LearnerProfileControls } from "./LearnerProfileControls";
import { renderWithI18n } from "./test/renderWithI18n";
import type { LearnerProfile, LoginSession } from "./types";

const session: LoginSession = {
  username: "student01",
  term: "Sommer 2026",
  roles: ["student"],
  courses: [
    { id: "martius-ml", title: "Machine Learning", professor: "Prof. M", term: "Sommer 2026" },
  ],
};

const profile: LearnerProfile = {
  onboarding_completed: true,
  learning_goal: "understand_deeply",
  preferences: {
    learning_goal: "understand_deeply",
    analogy: "football",
    onboarding_completed: true,
  },
  global_notes: "Prefers short summaries.",
  global_files: [],
  courses: [
    {
      course_id: "martius-ml",
      memory: "Needs more Bayes examples.",
      passed_lecture_ids: ["lecture-01"],
      files: [
        {
          path: "lectures/lecture-01/canvas/student/summary.md",
          size_bytes: 12,
          content: "# Summary",
        },
      ],
    },
  ],
};

describe("LearnerProfileControls", () => {
  it("shows stored memory and every course file with controls", async () => {
    const user = userEvent.setup();
    const removePreference = vi.fn().mockResolvedValue(undefined);
    renderWithI18n(
      <LearnerProfileControls
        session={session}
        state={{
          profile,
          loading: false,
          error: null,
          saveCalibration: vi.fn(),
          removePreference,
          clearMemory: vi.fn(),
          refresh: vi.fn(),
        }}
      />,
    );

    expect(screen.getByText("Prefers short summaries.")).toBeInTheDocument();
    expect(screen.getByText("Needs more Bayes examples.")).toBeInTheDocument();
    expect(screen.getByText("lectures/lecture-01/canvas/student/summary.md")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /remove analogy/i }));
    expect(removePreference).toHaveBeenCalledWith("analogy");
  });
});
