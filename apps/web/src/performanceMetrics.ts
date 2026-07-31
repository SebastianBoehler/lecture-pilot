import type { CourseLectureAnalytics, Lecture, LectureAnalyticsSummary } from "./types";

export type LectureSnapshot = {
  events: number;
  gateRate: string;
  learners: number;
  quizRate: string;
  status: "healthy" | "watch" | "needs-attention" | "no-data";
};

export type AnalyticsSignals = {
  attendance: Record<string, number>;
  gateRate: number | null;
  learners: number;
  quizRate: number | null;
};

export function lectureSnapshot(
  lecture: Lecture,
  analytics: LectureAnalyticsSummary | null,
): LectureSnapshot {
  if (analytics?.total_events) {
    const signals = analyticsSignals(analytics);
    return {
      events: analytics.total_events,
      gateRate: percent(signals.gateRate),
      learners: signals.learners,
      quizRate: percent(signals.quizRate),
      status: statusFor(signals.quizRate, signals.gateRate),
    };
  }
  return {
    events: 0,
    gateRate: "n/a",
    learners: 0,
    quizRate: "n/a",
    status: "no-data",
  };
}

export function analyticsSignals(analytics: LectureAnalyticsSummary): AnalyticsSignals {
  const attempts = analytics.quizzes.reduce((sum, quiz) => sum + quiz.total_attempts, 0);
  const correct = analytics.quizzes.reduce((sum, quiz) => sum + quiz.correct_attempts, 0);
  const passed = analytics.gates.reduce((sum, gate) => sum + (gate.status_counts.passed ?? 0), 0);
  const checks = analytics.gates.reduce((sum, gate) => sum + gate.total_events, 0);
  const attendance = [...analytics.quizzes, ...analytics.gates].reduce<Record<string, number>>(
    (totals, item) => {
      for (const [label, value] of Object.entries(item.attendance_split)) {
        totals[label] = (totals[label] ?? 0) + value;
      }
      return totals;
    },
    {},
  );
  return {
    attendance,
    gateRate: checks ? passed / checks : null,
    learners: Math.max(
      0,
      ...analytics.quizzes.map((quiz) => quiz.unique_learners),
      ...analytics.gates.map((gate) => gate.unique_learners),
    ),
    quizRate: attempts ? correct / attempts : null,
  };
}

export function courseLectureSnapshot(analytics: CourseLectureAnalytics): LectureSnapshot {
  return {
    events: analytics.total_events,
    gateRate: percent(analytics.gate_rate),
    learners: analytics.unique_learners,
    quizRate: percent(analytics.quiz_rate),
    status: analytics.total_events
      ? statusFor(analytics.quiz_rate, analytics.gate_rate)
      : "no-data",
  };
}

export function percent(value: number | null) {
  return value === null ? "n/a" : `${Math.round(value * 100)}%`;
}

export function splitBars(values: Record<string, number>) {
  const total = Object.values(values).reduce((sum, value) => sum + value, 0);
  return Object.entries(values).map(([label, value]) => ({
    label: label.replaceAll("_", " "),
    total,
    value,
  }));
}

function statusFor(quizRate: number | null, gateRate: number | null): LectureSnapshot["status"] {
  if ((quizRate !== null && quizRate < 0.58) || (gateRate !== null && gateRate < 0.6)) {
    return "needs-attention";
  }
  if ((quizRate !== null && quizRate < 0.72) || (gateRate !== null && gateRate < 0.72)) {
    return "watch";
  }
  return "healthy";
}
