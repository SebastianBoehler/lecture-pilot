import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PracticeExamView } from "./PracticeExamView";
import { renderWithI18n } from "./test/renderWithI18n";
import type { PracticeExam } from "./practiceExamTypes";
import type { LoginSession } from "./types";

describe("PracticeExamView", () => {
  it("renders supported Markdown and LaTeX in learner-facing exam content", () => {
    renderWithI18n(
      <PracticeExamView courseId="course-1" exam={exam} session={session} onClose={vi.fn()} />,
    );

    expect(screen.getByText("show your reasoning").closest("strong")).not.toBeNull();
    expect(screen.getByText("new").tagName).toBe("CODE");
    expect(screen.getByText("Maximum likelihood").closest("em")).not.toBeNull();
    expect(document.querySelectorAll(".katex")).toHaveLength(2);
  });

  it("separates the question-number styling from the rendered prompt", () => {
    renderWithI18n(
      <PracticeExamView courseId="course-1" exam={exam} session={session} onClose={vi.fn()} />,
    );

    const legend = screen.getByText("Question 1").closest("legend");
    const number = screen.getByText("Question 1");
    const prompt = legend?.children.item(1);

    expect(prompt).not.toBeNull();
    expect(number).toHaveClass("practice-question-number");
    expect(prompt).toHaveClass("practice-question-prompt");
    expect(number).not.toContainElement(prompt as HTMLElement);
  });
});

const session: LoginSession = {
  username: "student-a",
  term: "Summer 2026",
  roles: ["student"],
  courses: [],
  access_token: "test-token",
};

const exam: PracticeExam = {
  id: "a".repeat(32),
  course_id: "course-1",
  title: "Language modeling practice exam",
  language: "en",
  instructions: ["Answer every question and **show your reasoning** with $P(x)$ when needed."],
  duration_minutes: 90,
  created_at: "2026-07-31T10:00:00Z",
  total_points: 3,
  questions: [
    {
      id: "q-01",
      kind: "multiple_choice",
      prompt: "Compute $P(w_i \\mid w_{i-1})$ for `new`.",
      points: 3,
      options: ["*Maximum likelihood*", "Uniform probability"],
    },
  ],
};
