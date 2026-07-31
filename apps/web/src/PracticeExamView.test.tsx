import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

  it("makes the professor-visibility boundary clear without interrupting the exam", () => {
    renderWithI18n(
      <PracticeExamView courseId="course-1" exam={exam} session={session} onClose={vi.fn()} />,
    );

    const notice = screen.getByRole("note", { name: "Not shared with course staff" });
    expect(notice).toHaveTextContent("Your professor and other course staff will never see");
    expect(notice).toHaveTextContent("personal practice and feedback");
    expect(notice).not.toHaveTextContent("submitted to LecturePilot");
    expect(notice.querySelector("svg")).toBeNull();
  });

  it("gives open-answer fields the full question width without a visible label", () => {
    renderWithI18n(
      <PracticeExamView courseId="course-1" exam={exam} session={session} onClose={vi.fn()} />,
    );

    const answer = screen.getByRole("textbox", { name: "Your answer for question 2" });
    expect(screen.queryByText("Your answer for question 2")).not.toBeInTheDocument();
    expect(answer.parentElement).toHaveProperty("tagName", "FIELDSET");
  });

  it("scores multiple choice locally and reveals full-credit open answers after finishing", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => json(solutionSheet)),
    );
    renderWithI18n(
      <PracticeExamView courseId="course-1" exam={exam} session={session} onClose={vi.fn()} />,
    );

    await user.click(screen.getByRole("radio", { name: "Uniform probability" }));
    await user.type(screen.getByLabelText("Your answer for question 2"), "My short attempt");
    await user.click(screen.getByRole("button", { name: "Finish and review" }));

    expect(await screen.findByRole("heading", { name: "Solution sheet" })).toBeInTheDocument();
    expect(screen.getByText("0 of 3 multiple-choice points")).toBeInTheDocument();
    expect(screen.getByText("My short attempt")).toBeInTheDocument();
    expect(screen.getByText("A full-credit answer uses the chain rule.")).toBeInTheDocument();
    expect(screen.getByText("States the chain rule")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download solutions PDF" })).toBeInTheDocument();
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
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
  total_points: 8,
  questions: [
    {
      id: "q-01",
      kind: "multiple_choice",
      prompt: "Compute $P(w_i \\mid w_{i-1})$ for `new`.",
      points: 3,
      options: ["*Maximum likelihood*", "Uniform probability"],
    },
    {
      id: "q-02",
      kind: "open_ended",
      prompt: "Explain the chain rule.",
      points: 5,
      options: [],
    },
  ],
};

const solutionSheet = {
  exam_id: exam.id,
  title: `${exam.title} solutions`,
  total_points: exam.total_points,
  questions: [
    {
      id: "q-01",
      kind: "multiple_choice",
      points: 3,
      answer_index: 0,
      reference_answer: null,
      rubric: [],
    },
    {
      id: "q-02",
      kind: "open_ended",
      points: 5,
      answer_index: null,
      reference_answer: "A full-credit answer uses the chain rule.",
      rubric: ["States the chain rule", "Applies it correctly"],
    },
  ],
};

function json(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
