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

  it("uses a compact numeric prefix instead of repeating the question label", () => {
    renderWithI18n(
      <PracticeExamView courseId="course-1" exam={exam} session={session} onClose={vi.fn()} />,
    );

    const number = screen.getByText("1.");
    const legend = number.closest("legend");
    const prompt = legend?.children.item(1);

    expect(prompt).not.toBeNull();
    expect(number).toHaveClass("practice-question-number");
    expect(number).toHaveAttribute("aria-hidden", "true");
    expect(prompt).toHaveClass("practice-question-prompt");
    expect(number).not.toContainElement(prompt as HTMLElement);
    expect(screen.queryByText("Question 1")).not.toBeInTheDocument();
  });

  it("makes the professor-visibility boundary clear without interrupting the exam", () => {
    renderWithI18n(
      <PracticeExamView courseId="course-1" exam={exam} session={session} onClose={vi.fn()} />,
    );

    const notice = screen.getByRole("note", { name: "Not shared with course staff" });
    expect(notice).toHaveTextContent("Course staff cannot access these answers");
    expect(notice).toHaveTextContent("privately for your tutor and later self-review");
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

  it("preserves an invalid question number without rendering an answer control", () => {
    const invalidExam: PracticeExam = {
      ...exam,
      questions: [
        ...exam.questions,
        {
          id: "q-03",
          kind: "open_ended",
          status: "invalid",
          prompt: "INVALID QUESTION — DO NOT SCORE.",
          points: 0,
          options: [],
        },
      ],
    };

    renderWithI18n(
      <PracticeExamView
        courseId="course-1"
        exam={invalidExam}
        session={session}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText("3.")).toBeInTheDocument();
    expect(screen.getByText("INVALID QUESTION — DO NOT SCORE.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Your answer for question 3")).not.toBeInTheDocument();
  });

  it("retries a failed save with the same frozen answer snapshot", async () => {
    const user = userEvent.setup();
    const submissions: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url, init) => {
        if (!String(url).endsWith("/attempts")) return json(solutionSheet);
        submissions.push(init.body);
        if (submissions.length === 1)
          return new Response(JSON.stringify({ detail: "Please retry saving." }), { status: 503 });
        return json({ ...JSON.parse(init.body), created_at: "2026-09-06T10:00:00Z" });
      }),
    );
    renderWithI18n(
      <PracticeExamView courseId="course-1" exam={exam} session={session} onClose={vi.fn()} />,
    );
    await user.type(screen.getByLabelText("Your answer for question 2"), "My answer");
    await user.click(screen.getByRole("button", { name: "Finish and review" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Please retry saving.");
    expect(screen.getByLabelText("Your answer for question 2")).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Finish and review" }));
    expect(await screen.findByRole("heading", { name: "Solution sheet" })).toBeInTheDocument();
    expect(submissions).toHaveLength(2);
    expect(submissions[0]).toBe(submissions[1]);
  });

  it("scores multiple choice locally and reveals full-credit open answers after finishing", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url, init) =>
        String(url).endsWith("/attempts")
          ? json({ ...JSON.parse(init.body), created_at: "2026-09-06T10:00:00Z" })
          : json(solutionSheet),
      ),
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
