import { describe, expect, it } from "vitest";

import { analyticsSignals, courseLectureSnapshot, lectureSnapshot } from "./performanceMetrics";

describe("lectureSnapshot", () => {
  it("labels missing learner activity as no data", () => {
    expect(lectureSnapshot(lecture(), null)).toMatchObject({
      events: 0,
      gateRate: "n/a",
      quizRate: "n/a",
      status: "no-data",
    });
  });

  it("uses current learner-level outcome cells instead of raw events", () => {
    expect(analyticsSignals(analytics())).toEqual({
      gateRate: 0.6,
      learners: 9,
      quizRate: 0.8,
      status: "available",
    });
    expect(lectureSnapshot(lecture(), analytics())).toMatchObject({
      gateRate: "60%",
      learners: 9,
      quizRate: "80%",
      status: "available",
    });
  });

  it("reports insufficient coverage without a threshold-derived warning", () => {
    const snapshot = courseLectureSnapshot({
      activity_events: 3,
      correction_after_feedback: cell("correction_after_feedback", 1, null),
      current_learning_map_revision: "map-2",
      current_publication_version: 2,
      delayed_transfer: cell("delayed_transfer", 0, null),
      independent_first_pass: cell("independent_first_pass", 0, null),
      lecture_id: "lecture-01",
      quiz_first_attempt: cell("quiz_first_attempt", 3, null),
      supported_retry: cell("supported_retry", 0, null),
      unique_learners: 3,
    });
    expect(snapshot.status).toBe("insufficient-data");
    expect(snapshot.quizRate).toBe("n/a");
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
    correction_after_feedback: cell("correction_after_feedback", 5, 0.4),
    current_learning_map_revision: "map-2",
    current_publication_version: 2,
    delayed_transfer: cell("delayed_transfer", 5, 0.4),
    gates: [
      {
        activity_events: 12,
        delayed_transfer: cell("delayed_transfer", 5, 0.8),
        gate_id: "gate-1",
        gate_revision: "revision-2",
        independent_first_pass: cell("independent_first_pass", 5, 0.2),
        learning_map_revision: "map-2",
        publication_version: 2,
        supported_retry: cell("supported_retry", 5, 0.8),
        unique_learners: 5,
        version_status: "current" as const,
      },
    ],
    lecture_id: "lecture-01",
    independent_first_pass: cell("independent_first_pass", 5, 0.6),
    quiz_first_attempt: cell("quiz_first_attempt", 5, 0.8),
    quizzes: [
      {
        activity_events: 10,
        component_id: "quiz-1",
        component_type: "quiz",
        correction_after_feedback: cell("correction_after_feedback", 3, null),
        first_attempt: cell("quiz_first_attempt", 5, 0.2),
        learning_map_revision: "map-2",
        options: [],
        publication_version: 2,
        question: "One",
        title: "One",
        unique_learners: 5,
        version_status: "current" as const,
      },
    ],
    activity_events: 22,
    supported_retry: cell("supported_retry", 5, 0.4),
    unique_learners: 9,
  };
}

function cell(evidenceType: string, sampleSize: number, rate: number | null) {
  return {
    data_status: rate === null ? ("insufficient_data" as const) : ("available" as const),
    evidence_type: evidenceType,
    rate,
    sample_size: sampleSize,
  };
}
