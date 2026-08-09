import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PerformanceInsights } from "./PerformanceInsights";
import { CoursePerformanceOverview } from "./CoursePerformanceOverview";
import { PerformanceOverview } from "./PerformanceOverview";
import { ProfessorLearningMapTree } from "./ProfessorLearningMapTree";
import { courseLectureSnapshot, lectureSnapshot } from "./performanceMetrics";
import { renderWithI18n } from "./test/renderWithI18n";
import type { LectureAnalyticsSummary } from "./types";

describe("professor learner-level outcomes", () => {
  it("shows quiz evidence type, denominator and version without a small-cell distribution", () => {
    renderWithI18n(<PerformanceInsights analytics={smallQuizAnalytics()} view="quizzes" />);

    expect(screen.getByText("First-attempt correctness")).toBeInTheDocument();
    expect(screen.getAllByText("Insufficient data · n=4")).toHaveLength(2);
    expect(screen.getByText("Publication v2 · current")).toBeInTheDocument();
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Answer distribution" })).not.toBeInTheDocument();
    expect(screen.queryByText("Distractor selected by one learner")).not.toBeInTheDocument();
  });

  it("keeps independent first pass, supported retry and delayed transfer separate", () => {
    renderWithI18n(<PerformanceInsights analytics={gateAnalytics(5)} view="gates" />);

    expect(screen.getByText("Independent first pass")).toBeInTheDocument();
    expect(screen.getByText("Supported retry")).toBeInTheDocument();
    expect(screen.getByText("Delayed transfer")).toBeInTheDocument();
    expect(screen.getAllByText(/n=5/)).toHaveLength(3);
    expect(screen.getByText("Gate revision revision-2")).toBeInTheDocument();
    expect(screen.getByText("60%")).toBeInTheDocument();
  });

  it("uses evidence availability instead of healthy, watch or attention ampels", () => {
    const snapshot = courseLectureSnapshot({
      activity_events: 12,
      correction_after_feedback: outcome("correction_after_feedback", 0, null),
      current_learning_map_revision: "map-revision-2",
      current_publication_version: 2,
      delayed_transfer: outcome("delayed_transfer", 0, null),
      independent_first_pass: outcome("independent_first_pass", 4, null),
      lecture_id: "lecture-01",
      quiz_first_attempt: outcome("quiz_first_attempt", 4, null),
      supported_retry: outcome("supported_retry", 0, null),
      unique_learners: 4,
    });

    expect(snapshot.status).toBe("insufficient-data");
    expect(JSON.stringify(snapshot)).not.toMatch(/healthy|watch|attention/);
  });

  it("does not paint a small learning-map gate as mastered", () => {
    const analytics = gateAnalytics(4);
    analytics.learning_map = learningMap();
    renderWithI18n(<ProfessorLearningMapTree analytics={analytics} />);

    const concept = screen.getByRole("button", { name: /decision making.*insufficient data/i });
    expect(concept).toBeVisible();
    fireEvent.click(concept);
    expect(screen.getByText("Publication v2 · current")).toBeInTheDocument();
    expect(screen.getByText("Learning map revision map-revision-2")).toBeInTheDocument();
    expect(screen.getByText("Gate revision revision-2")).toBeInTheDocument();
    expect(
      screen.getByText("Independent first pass · Insufficient data · n=4"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/100% passed/i)).not.toBeInTheDocument();
    expect(document.querySelector(".is-healthy, .is-watch, .is-attention")).toBeNull();
  });

  it("labels the lecture overview with its captured versions, evidence and denominators", () => {
    const analytics = gateAnalytics(5);
    renderWithI18n(<PerformanceOverview snapshot={lectureSnapshot(lecture(), analytics)} />);

    expect(screen.getByText("Publication v2")).toBeInTheDocument();
    expect(screen.getByText("Learning map revision map-revision-2")).toBeInTheDocument();
    expect(
      screen.getByText("First-attempt correctness · Insufficient data · n=0"),
    ).toBeInTheDocument();
    expect(screen.getByText("Independent first pass · Available · n=5")).toBeInTheDocument();
  });

  it("shows each course lecture's publication and map revision", () => {
    const analytics = gateAnalytics(5);
    renderWithI18n(
      <CoursePerformanceOverview
        analytics={{
          ...analytics,
          lectures: [
            {
              ...analytics,
              current_learning_map_revision: analytics.current_learning_map_revision,
              lecture_id: analytics.lecture_id,
            },
          ],
        }}
        lectures={[lecture()]}
        onSelectLecture={() => undefined}
      />,
    );

    expect(
      screen.getByText(
        (_, element) =>
          element?.tagName === "SMALL" &&
          element.textContent === "Publication v2 · Learning map revision map-revision-2",
      ),
    ).toBeInTheDocument();
  });
});

function lecture() {
  return {
    attendance: "unknown" as const,
    date: "2026-06-01",
    id: "lecture-01",
    number: "01",
    title: "Risk lecture",
  };
}

function smallQuizAnalytics(): LectureAnalyticsSummary {
  return {
    course_id: "demo-course",
    correction_after_feedback: outcome("correction_after_feedback", 2, null),
    current_learning_map_revision: "map-revision-2",
    current_publication_version: 2,
    delayed_transfer: outcome("delayed_transfer", 0, null),
    gates: [],
    lecture_id: "lecture-01",
    independent_first_pass: outcome("independent_first_pass", 0, null),
    quiz_first_attempt: outcome("quiz_first_attempt", 4, null),
    quizzes: [
      {
        activity_events: 10,
        component_id: "risk-check",
        component_type: "single_choice_quiz",
        correction_after_feedback: outcome("correction_after_feedback", 2, null),
        first_attempt: outcome("quiz_first_attempt", 4, null),
        learning_map_revision: "map-revision-2",
        options: null,
        publication_version: 2,
        question: "Which action minimizes expected risk?",
        title: "Risk threshold check",
        unique_learners: 4,
        version_status: "current",
      },
    ],
    activity_events: 10,
    supported_retry: outcome("supported_retry", 0, null),
    unique_learners: 4,
  };
}

function gateAnalytics(sampleSize: number): LectureAnalyticsSummary {
  return {
    course_id: "demo-course",
    correction_after_feedback: outcome("correction_after_feedback", 0, null),
    current_learning_map_revision: "map-revision-2",
    current_publication_version: 2,
    gates: [
      {
        activity_events: sampleSize,
        delayed_transfer: outcome("delayed_transfer", sampleSize, sampleSize === 5 ? 0.8 : null),
        gate_id: "risk-gate",
        gate_revision: "revision-2",
        independent_first_pass: outcome(
          "independent_first_pass",
          sampleSize,
          sampleSize === 5 ? 0.6 : null,
        ),
        learning_map_revision: "map-revision-2",
        publication_version: 2,
        supported_retry: outcome("supported_retry", sampleSize, sampleSize === 5 ? 0.8 : null),
        unique_learners: sampleSize,
        version_status: "current",
      },
    ],
    lecture_id: "lecture-01",
    independent_first_pass: outcome(
      "independent_first_pass",
      sampleSize,
      sampleSize === 5 ? 0.6 : null,
    ),
    quiz_first_attempt: outcome("quiz_first_attempt", 0, null),
    quizzes: [],
    activity_events: sampleSize,
    delayed_transfer: outcome("delayed_transfer", sampleSize, sampleSize === 5 ? 0.8 : null),
    supported_retry: outcome("supported_retry", sampleSize, sampleSize === 5 ? 0.8 : null),
    unique_learners: sampleSize,
  };
}

function outcome(evidenceType: string, sampleSize: number, rate: number | null) {
  return {
    data_status: rate === null ? ("insufficient_data" as const) : ("available" as const),
    evidence_type: evidenceType,
    rate,
    sample_size: sampleSize,
  };
}

function learningMap() {
  return {
    course_id: "demo-course",
    gates: [
      {
        concept_id: "aim",
        evidence_required: "Connect posterior and loss.",
        id: "risk-gate",
        prompt: "Explain expected risk.",
        section_id: "aim",
        source_ref: "Lecture03-eng.tex#aim",
        title: "Risk evidence gate",
      },
    ],
    lecture_id: "lecture-01",
    nodes: [
      {
        gate_ids: ["risk-gate"],
        id: "aim",
        lecture_id: "lecture-01",
        prerequisites: [],
        quiz_ids: [],
        section_id: "aim",
        source_ref: "Lecture03-eng.tex#aim",
        title: "Decision making",
      },
    ],
    title: "Bayesian decision theory",
  };
}
