import type { Lecture, LectureAnalyticsSummary } from "./types";

export type LectureSnapshot = {
  events: number;
  gateRate: string;
  learners: number;
  quizRate: string;
  status: "healthy" | "watch" | "needs-attention";
};

export function lectureSnapshot(lecture: Lecture, analytics: LectureAnalyticsSummary | null): LectureSnapshot {
  if (analytics?.total_events) {
    const attempts = analytics.quizzes.reduce((sum, quiz) => sum + quiz.total_attempts, 0);
    const correct = analytics.quizzes.reduce((sum, quiz) => sum + quiz.correct_attempts, 0);
    const passed = analytics.gates.reduce((sum, gate) => sum + (gate.status_counts.passed ?? 0), 0);
    const checks = analytics.gates.reduce((sum, gate) => sum + gate.total_events, 0);
    const learners = Math.max(
      0,
      ...analytics.quizzes.map((quiz) => quiz.unique_learners),
      ...analytics.gates.map((gate) => gate.unique_learners),
    );
    return {
      events: analytics.total_events,
      gateRate: checks ? percent(passed / checks) : "n/a",
      learners,
      quizRate: attempts ? percent(correct / attempts) : "n/a",
      status: statusFor(attempts ? correct / attempts : 0.5, checks ? passed / checks : 0.5),
    };
  }
  return {
    events: 0,
    gateRate: "n/a",
    learners: 0,
    quizRate: "n/a",
    status: "watch",
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

function statusFor(quizRate: number, gateRate: number): LectureSnapshot["status"] {
  if (quizRate < 0.58 || gateRate < 0.6) return "needs-attention";
  if (quizRate < 0.72 || gateRate < 0.72) return "watch";
  return "healthy";
}
