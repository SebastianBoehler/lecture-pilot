import { describe, expect, it } from "vitest";

import { analyticsSignals, lectureSnapshot } from "./performanceMetrics";

describe("lectureSnapshot", () => {
  it("labels missing learner activity as no data rather than a warning state", () => {
    expect(lectureSnapshot(lecture(), null)).toMatchObject({
      events: 0,
      gateRate: "n/a",
      quizRate: "n/a",
      status: "no-data",
    });
  });

  it("aggregates every quiz and gate for the overview and signal charts", () => {
    expect(analyticsSignals(analytics())).toEqual({
      attendance: { absent: 3, present: 9 },
      gateRate: 0.75,
      learners: 6,
      quizRate: 0.6,
    });

    expect(lectureSnapshot(lecture(), analytics())).toMatchObject({
      gateRate: "75%",
      learners: 6,
      quizRate: "60%",
    });
  });
});

function lecture() {
  return {
    attendance: "unknown" as const,
    date: "2026-05-09",
    id: "lecture-01",
    number: "01",
    title: "Introduction",
  };
}

function analytics() {
  return {
    course_id: "course-1",
    lecture_id: "lecture-01",
    total_events: 14,
    quizzes: [
      {
        attendance_split: { absent: 1, present: 4 },
        component_id: "quiz-1",
        component_type: "quiz",
        correct_attempts: 2,
        correct_rate: 0.4,
        options: [],
        question: "One",
        title: "One",
        total_attempts: 5,
        unique_learners: 5,
      },
      {
        attendance_split: { absent: 1, present: 4 },
        component_id: "quiz-2",
        component_type: "quiz",
        correct_attempts: 4,
        correct_rate: 0.8,
        options: [],
        question: "Two",
        title: "Two",
        total_attempts: 5,
        unique_learners: 6,
      },
    ],
    gates: [
      {
        attendance_split: { absent: 1, present: 1 },
        gate_id: "gate-1",
        status_counts: { failed: 1, passed: 3 },
        total_events: 4,
        unique_learners: 4,
        independent_attempts: 2,
        independent_passes: 2,
        supported_attempts: 2,
        transfer_attempts: 1,
        independent_transfer_passes: 1,
        assistance_level_counts: { none: 2, prompt: 2 },
        evidence_counts: {},
      },
    ],
  };
}
