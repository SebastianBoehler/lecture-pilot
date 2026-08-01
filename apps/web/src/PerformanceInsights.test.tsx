import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { PerformanceInsights } from "./PerformanceInsights";
import { renderWithI18n } from "./test/renderWithI18n";
import type { LectureAnalyticsSummary } from "./types";

describe("PerformanceInsights", () => {
  it("shows independent learning, scaffold use, and demonstrated evidence", () => {
    renderWithI18n(<PerformanceInsights analytics={analytics()} view="gates" />);

    expect(screen.getByRole("heading", { name: "Independent learning" })).toBeInTheDocument();
    expect(screen.getByText("Independent attempts")).toBeInTheDocument();
    expect(screen.getByText("Supported attempts")).toBeInTheDocument();
    expect(screen.getByText("Independent transfer passes")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Scaffolds used" })).toBeInTheDocument();
    expect(screen.getByText("worked step")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Demonstrated evidence" })).toBeInTheDocument();
    expect(screen.getByText("risk calculation")).toBeInTheDocument();
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
    lecture_id: "lecture-01",
    total_events: 4,
    unique_learners: 2,
    quizzes: [],
    gates: [
      {
        gate_id: "risk-gate",
        total_events: 4,
        unique_learners: 2,
        status_counts: { needs_evidence: 2, passed: 2 },
        attendance_split: { present: 4 },
        independent_attempts: 2,
        independent_passes: 1,
        supported_attempts: 2,
        transfer_attempts: 1,
        independent_transfer_passes: 1,
        assistance_level_counts: { none: 2, worked_step: 2 },
        evidence_counts: { risk_calculation: 2 },
      },
    ],
  };
}

function quizAnalytics(): LectureAnalyticsSummary {
  return {
    course_id: "demo-course",
    lecture_id: "lecture-01",
    total_events: 4,
    unique_learners: 2,
    gates: [],
    quizzes: [quiz("quiz-1", "First question", 0.5), quiz("quiz-2", "Second question", 1)],
  };
}

function quiz(componentId: string, question: string, correctRate: number) {
  return {
    attendance_split: { present: 2 },
    component_id: componentId,
    component_type: "quiz" as const,
    correct_attempts: correctRate === 1 ? 2 : 1,
    correct_rate: correctRate,
    options: [
      { correct: true, option_index: 0, selections: 1, text: "Correct answer" },
      { correct: false, option_index: 1, selections: 1, text: "Distractor" },
    ],
    question,
    title: "Checkpoint quiz",
    total_attempts: 2,
    unique_learners: 2,
  };
}
