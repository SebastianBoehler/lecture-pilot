import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ExamReadinessResult } from "./ExamReadinessResult";
import { renderWithI18n } from "./test/renderWithI18n";
import type {
  ExamReadinessAttemptResult,
  ExamReadinessCheck,
  ExamRevisionTask,
  Lecture,
} from "./types";

describe("ExamReadinessResult", () => {
  it("keeps a long review plan compact until the learner asks for more", async () => {
    const user = userEvent.setup();
    renderWithI18n(
      <ExamReadinessResult
        check={check}
        lectures={[lecture]}
        result={resultWithTasks(5)}
        onOpenLecture={vi.fn()}
      />,
    );

    expect(screen.getByRole("heading", { name: "Topic 1" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Topic 4" })).not.toBeVisible();
    expect(screen.getAllByRole("button", { name: /review lecture 03/i })).toHaveLength(1);

    await user.click(screen.getByText(/show 2 more priorities/i));

    expect(screen.getByRole("heading", { name: "Topic 4" })).toBeVisible();
  });

  it("keeps an unscored legacy open-answer result neutral", () => {
    renderWithI18n(
      <ExamReadinessResult
        check={check}
        lectures={[lecture]}
        result={pendingResult()}
        onOpenLecture={vi.fn()}
      />,
    );

    expect(screen.getByRole("heading", { name: "Result pending" })).toHaveFocus();
    expect(screen.queryByRole("heading", { name: "Keep reviewing" })).not.toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText(/no readiness score has been assigned/i)).toBeInTheDocument();
  });
});

const lecture: Lecture = {
  id: "lecture-03",
  number: "03",
  title: "Bayesian Decision Theory",
  date: "2026-04-29",
  attendance: "unknown",
};

const check: ExamReadinessCheck = {
  course_id: "martius-ml",
  passing_score: 0.7,
  published_lecture_count: 1,
  coverage: [],
  questions: [],
};

function resultWithTasks(count: number): ExamReadinessAttemptResult {
  return {
    course_id: "martius-ml",
    passing_score: 0.7,
    score: 0.4,
    guidance_level: "scaffolded",
    results: [],
    tasks: Array.from({ length: count }, (_, index) => task(index + 1)),
  };
}

function pendingResult(): ExamReadinessAttemptResult {
  return {
    ...resultWithTasks(1),
    score: null,
    results: [
      {
        question_id: "question-1",
        kind: "open_ended",
        lecture_id: "lecture-03",
        section_id: "topic-1",
        answer_kind: "open_ended",
        correct: null,
        status: "needs_rubric_review",
      },
    ],
  };
}

function task(index: number): ExamRevisionTask {
  return {
    id: `task-${index}`,
    question_id: `question-${index}`,
    kind: "review_wrong_mc",
    status: "open",
    guidance_level: "scaffolded",
    lecture_id: "lecture-03",
    lecture_title: "Bayesian Decision Theory",
    section_id: `topic-${index}`,
    section_title: `Topic ${index}`,
    prompt: `Question ${index}`,
    source_ref: `Lecture03-eng.tex frame ${index}`,
    rubric: [`Evidence ${index}`],
    expected_evidence: `Evidence ${index}`,
    next_action: `Review topic ${index}, then answer again without options.`,
    scaffold_policy: {
      trigger: "readiness_task",
      learner_stage: "novice",
      profile: "worked_example",
      process_label: "scaffolded_reasoning",
      tutor_move: "Ask for evidence.",
      forbidden: "Reveal the answer.",
    },
  };
}
