import type {
  AnalyticsOutcomeCell,
  CourseLectureAnalytics,
  Lecture,
  LectureAnalyticsSummary,
} from "./types";

export type EvidenceStatus = "available" | "insufficient-data" | "historical-only" | "no-data";

export type LectureSnapshot = {
  events: number;
  gateEvidence: AnalyticsOutcomeCell | null;
  gateRate: string;
  learners: number;
  learningMapRevision: string | null;
  publicationVersion: number | null;
  quizEvidence: AnalyticsOutcomeCell | null;
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
  if (!analytics) return emptySnapshot();
  const signals = analyticsSignals(analytics);
  return {
    events: analytics.activity_events,
    gateEvidence: analytics.independent_first_pass,
    gateRate: percent(signals.gateRate),
    learners: analytics.unique_learners,
    learningMapRevision: analytics.current_learning_map_revision,
    publicationVersion: analytics.current_publication_version,
    quizEvidence: analytics.quiz_first_attempt,
    quizRate: percent(signals.quizRate),
    status: signals.status,
  };
}

export function analyticsSignals(analytics: LectureAnalyticsSummary): AnalyticsSignals {
  const currentCells = [analytics.quiz_first_attempt, analytics.independent_first_pass];
  return {
    gateRate: analytics.independent_first_pass.rate,
    learners: analytics.unique_learners,
    quizRate: analytics.quiz_first_attempt.rate,
    status: evidenceStatus(analytics.activity_events, currentCells),
  };
}

export function courseLectureSnapshot(analytics: CourseLectureAnalytics): LectureSnapshot {
  const cells = [analytics.quiz_first_attempt, analytics.independent_first_pass];
  return {
    events: analytics.activity_events,
    gateEvidence: analytics.independent_first_pass,
    gateRate: percent(analytics.independent_first_pass.rate),
    learners: analytics.unique_learners,
    learningMapRevision: analytics.current_learning_map_revision,
    publicationVersion: analytics.current_publication_version,
    quizEvidence: analytics.quiz_first_attempt,
    quizRate: percent(analytics.quiz_first_attempt.rate),
    status: evidenceStatus(analytics.activity_events, cells),
  };
}

export function percent(value: number | null) {
  return value === null ? "n/a" : `${Math.round(value * 100)}%`;
}

function evidenceStatus(activityEvents: number, cells: AnalyticsOutcomeCell[]): EvidenceStatus {
  if (!activityEvents) return "no-data";
  if (cells.some((cell) => cell.data_status === "available")) return "available";
  if (cells.some((cell) => cell.sample_size > 0)) return "insufficient-data";
  return "historical-only";
}

function emptySnapshot(): LectureSnapshot {
  return {
    events: 0,
    gateEvidence: null,
    gateRate: "n/a",
    learners: 0,
    learningMapRevision: null,
    publicationVersion: null,
    quizEvidence: null,
    quizRate: "n/a",
    status: "no-data",
  };
}
