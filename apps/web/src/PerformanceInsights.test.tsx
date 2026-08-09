import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { PerformanceInsights } from "./PerformanceInsights";
import { renderWithI18n } from "./test/renderWithI18n";
import type { LectureAnalyticsSummary } from "./types";

describe("PerformanceInsights", () => {
  it("shows independent, supported and delayed learner-level evidence", () => {
    renderWithI18n(<PerformanceInsights analytics={analytics()} view="gates" />);

    expect(screen.getByText("Independent first pass")).toBeInTheDocument();
    expect(screen.getByText("Supported retry")).toBeInTheDocument();
    expect(screen.getByText("Delayed transfer")).toBeInTheDocument();
    expect(screen.getByText("Gate revision revision-1")).toBeInTheDocument();
  });

  it("shows one full-size quiz detail at a time", async () => {
    const user = userEvent.setup();
    renderWithI18n(<PerformanceInsights analytics={quizAnalytics()} view="quizzes" />);

    expect(screen.getByRole("heading", { name: "First question" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Second question" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /second question/i }));

    expect(screen.getByRole("heading", { name: "Second question" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "First question" })).not.toBeInTheDocument();
  });
});

function analytics(): LectureAnalyticsSummary {
  return {
    course_id: "demo-course",
    current_learning_map_revision: "map-1",
    current_publication_version: 1,
    correction_after_feedback: outcome("correction_after_feedback", 0.5),
    delayed_transfer: outcome("delayed_transfer", 0.8),
    independent_first_pass: outcome("independent_first_pass", 0.6),
    lecture_id: "lecture-01",
    activity_events: 15,
    unique_learners: 5,
    quizzes: [],
    quiz_first_attempt: outcome("quiz_first_attempt", 0.6),
    supported_retry: outcome("supported_retry", 0.8),
    gates: [
      {
        activity_events: 15,
        delayed_transfer: outcome("delayed_transfer", 0.8),
        gate_id: "risk-gate",
        gate_revision: "revision-1",
        independent_first_pass: outcome("independent_first_pass", 0.6),
        learning_map_revision: "map-1",
        publication_version: 1,
        supported_retry: outcome("supported_retry", 0.8),
        unique_learners: 5,
        version_status: "current",
      },
    ],
  };
}

function quizAnalytics(): LectureAnalyticsSummary {
  return {
    ...analytics(),
    gates: [],
    quizzes: [quiz("quiz-1", "First question", 0.6), quiz("quiz-2", "Second question", 1)],
  };
}

function quiz(componentId: string, question: string, rate: number) {
  return {
    activity_events: 5,
    component_id: componentId,
    component_type: "quiz",
    correction_after_feedback: outcome("correction_after_feedback", 0.5),
    first_attempt: outcome("quiz_first_attempt", rate),
    learning_map_revision: "map-1",
    options: [
      { correct: true, option_index: 0, selections: 3, text: "Correct answer" },
      { correct: false, option_index: 1, selections: 2, text: "Distractor" },
    ],
    publication_version: 1,
    question,
    title: "Checkpoint quiz",
    unique_learners: 5,
    version_status: "current" as const,
  };
}

function outcome(evidenceType: string, rate: number) {
  return { data_status: "available" as const, evidence_type: evidenceType, rate, sample_size: 5 };
}
