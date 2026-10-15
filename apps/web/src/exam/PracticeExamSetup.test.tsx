import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PracticeExamSetup } from "./PracticeExamSetup";
import { renderWithI18n } from "../test/renderWithI18n";
import type { UniversityCourse } from "../shared/types";

describe("PracticeExamSetup", () => {
  it("lets the learner choose four-option multiple-answer practice with deductions", async () => {
    const generate = vi.fn();
    const user = userEvent.setup();
    renderWithI18n(
      <PracticeExamSetup
        course={course}
        error={null}
        generating={false}
        onClose={vi.fn()}
        onGenerate={generate}
      />,
    );
    await user.selectOptions(screen.getByLabelText("Multiple-choice format"), "multiple_answers");
    expect(screen.getByText(/4 points for the complete correct set/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Generate 25-question exam" }));
    expect(generate).toHaveBeenCalledWith({
      question_count: 25,
      duration_minutes: 90,
      choice_format: "multiple_answers",
    });
  });
});

const course: UniversityCourse = {
  id: "course-1",
  title: "Natural Language Processing",
  professor: "Professor",
  term: "Summer 2026",
};
