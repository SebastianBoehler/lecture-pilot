import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PerformanceInsights } from "./PerformanceInsights";
import { renderWithI18n } from "./test/renderWithI18n";
import type { LectureAnalyticsSummary } from "./types";

describe("PerformanceInsights", () => {
  it("shows independent learning, scaffold use, and demonstrated evidence", () => {
    renderWithI18n(<PerformanceInsights analytics={analytics()} />);

    expect(screen.getByRole("heading", { name: "Independent learning" })).toBeInTheDocument();
    expect(screen.getByText("Independent attempts")).toBeInTheDocument();
    expect(screen.getByText("Supported attempts")).toBeInTheDocument();
    expect(screen.getByText("Independent transfer passes")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Scaffolds used" })).toBeInTheDocument();
    expect(screen.getByText("worked step")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Demonstrated evidence" })).toBeInTheDocument();
    expect(screen.getByText("risk calculation")).toBeInTheDocument();
  });
});

function analytics(): LectureAnalyticsSummary {
  return {
    course_id: "demo-course",
    lecture_id: "lecture-01",
    total_events: 4,
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
