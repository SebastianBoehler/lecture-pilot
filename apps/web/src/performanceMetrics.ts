import type {
  AnalyticsOutcomeCell,
  CourseLectureAnalytics,
  Lecture,
  LectureAnalyticsSummary,
} from "./types";

export type EvidenceStatus = "available" | "insufficient-data" | "historical-only" | "no-data";

export type LectureSnapshot = {
  events: number;
  gateRate: string;
  learners: number;
  quizRate: string;
  status: EvidenceStatus;
};

export type AnalyticsSignals = {
  gateRate: number | null;
  learners: number;
  quizRate: number | null;
  status: EvidenceStatus;
};

export function lectureSnapshot(
  _lecture: Lecture,
  analytics: LectureAnalyticsSummary | null,
): LectureSnapshot {
  if (!analytics?.activity_events) return emptySnapshot();
  const signals = analyticsSignals(analytics);
  return {
    events: analytics.activity_events,
    gateRate: percent(signals.gateRate),
    learners: analytics.unique_learners,
    quizRate: percent(signals.quizRate),
    status: signals.status,
  };
}

export function analyticsSignals(analytics: LectureAnalyticsSummary): AnalyticsSignals {
  const quizCells = analytics.quizzes
    .filter((quiz) => quiz.version_status === "current")
    .map((quiz) => quiz.first_attempt);
  const gateCells = analytics.gates
    .filter((gate) => gate.version_status === "current")
    .map((gate) => gate.independent_first_pass);
  const currentCells = [...quizCells, ...gateCells];
  return {
    gateRate: weightedRate(gateCells),
    learners: analytics.unique_learners,
    quizRate: weightedRate(quizCells),
    status: evidenceStatus(analytics.activity_events, currentCells),
  };
}

export function courseLectureSnapshot(analytics: CourseLectureAnalytics): LectureSnapshot {
  const cells = [analytics.quiz_first_attempt, analytics.independent_first_pass];
  return {
    events: analytics.activity_events,
    gateRate: percent(analytics.independent_first_pass.rate),
    learners: analytics.unique_learners,
    quizRate: percent(analytics.quiz_first_attempt.rate),
    status: evidenceStatus(analytics.activity_events, cells),
  };
}

export function percent(value: number | null) {
  return value === null ? "n/a" : `${Math.round(value * 100)}%`;
}

function weightedRate(cells: AnalyticsOutcomeCell[]) {
  const available = cells.filter(
    (cell): cell is AnalyticsOutcomeCell & { rate: number } => cell.rate !== null,
  );
  const denominator = available.reduce((sum, cell) => sum + cell.sample_size, 0);
  if (!denominator) return null;
  return available.reduce((sum, cell) => sum + cell.rate * cell.sample_size, 0) / denominator;
}

function evidenceStatus(activityEvents: number, cells: AnalyticsOutcomeCell[]): EvidenceStatus {
  if (!activityEvents) return "no-data";
  if (cells.some((cell) => cell.data_status === "available")) return "available";
  if (cells.some((cell) => cell.sample_size > 0)) return "insufficient-data";
  return "historical-only";
}

function emptySnapshot(): LectureSnapshot {
  return { events: 0, gateRate: "n/a", learners: 0, quizRate: "n/a", status: "no-data" };
}
