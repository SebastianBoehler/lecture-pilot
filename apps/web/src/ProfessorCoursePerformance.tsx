import { useState, type CSSProperties } from "react";

import { getLectureAnalytics } from "./analyticsApi";
import type {
  AnalyticsGateMetric,
  AnalyticsQuizMetric,
  Lecture,
  LectureAnalyticsSummary,
  LoginSession,
  UniversityCourse,
} from "./types";

const demoPerformanceCourse: UniversityCourse = {
  id: "martius-ml",
  title: "Grundlagen des Maschinellen Lernens",
  professor: "Prof. Georg Martius",
  term: "Sommer 2026",
};

export function ProfessorCoursePerformance({
  lectures,
  session,
  onBack,
}: {
  lectures: Lecture[];
  session: LoginSession;
  onBack: () => void;
}) {
  const course = session.courses.find((item) => item.id === demoPerformanceCourse.id) ?? demoPerformanceCourse;
  const [selectedLecture, setSelectedLecture] = useState(lectures[2] ?? lectures[0]);
  const [analytics, setAnalytics] = useState<LectureAnalyticsSummary | null>(null);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);

  async function refreshAnalytics(lecture = selectedLecture) {
    setAnalyticsError(null);
    setSelectedLecture(lecture);
    try {
      setAnalytics(await getLectureAnalytics(course.id, lecture.id, session));
    } catch (error) {
      setAnalyticsError(error instanceof Error ? error.message : "Lecture analytics loading failed.");
    }
  }

  return (
    <main className="professor-screen">
      <section className="dashboard-header">
        <button className="ghost-button" type="button" onClick={onBack}>Back</button>
        <p className="section-label">Professor workspace</p>
        <h1>Course performance</h1>
        <p>Anonymous quiz and quality-gate aggregates for published tutor workspaces.</p>
      </section>
      <section className="course-panel" aria-labelledby="course-performance-title">
        <div className="panel-heading">
          <h2 id="course-performance-title">{course.title}</h2>
          <span>{course.term}</span>
        </div>
        <div className="performance-layout">
          <nav className="performance-lecture-list" aria-label="Performance lecture list">
            {lectures.map((lecture) => (
              <button
                className={lecture.id === selectedLecture.id ? "is-active" : undefined}
                key={lecture.id}
                type="button"
                onClick={() => void refreshAnalytics(lecture)}
              >
                <span>{lecture.number}</span>
                <strong>{lecture.title}</strong>
                <small>{lecture.date}</small>
              </button>
            ))}
          </nav>
          <section className="flow-card analytics-card" aria-live="polite">
            <header className="analytics-page-heading">
              <div>
                <p className="section-label">Lecture {selectedLecture.number}</p>
                <h2>{selectedLecture.title}</h2>
              </div>
              <button type="button" onClick={() => void refreshAnalytics()}>
                Refresh analytics
              </button>
            </header>
            {analyticsError ? <p className="form-error">{analyticsError}</p> : null}
            {analytics ? <AnalyticsSummary analytics={analytics} /> : (
              <p className="drawer-note">Select a lecture or refresh to load performance data.</p>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}

function AnalyticsSummary({ analytics }: { analytics: LectureAnalyticsSummary }) {
  if (!analytics.total_events) {
    return <p className="drawer-note">No quiz or gate events recorded for this lecture yet.</p>;
  }
  return (
    <div className="analytics-summary">
      <SummaryTiles analytics={analytics} />
      {analytics.quizzes.map((quiz) => (
        <article className="analytics-panel" key={quiz.component_id}>
          <header>
            <span>Quiz</span>
            <strong>{quiz.title}</strong>
            <small>{percent(quiz.correct_rate)} correct · {quiz.unique_learners} learners</small>
          </header>
          <p>{quiz.question}</p>
          <QuizInsight quiz={quiz} />
        </article>
      ))}
      {analytics.gates.map((gate) => (
        <article className="analytics-panel" key={gate.gate_id}>
          <header>
            <span>Gate</span>
            <strong>{gate.gate_id}</strong>
            <small>{gate.total_events} checks · {gate.unique_learners} learners</small>
          </header>
          <GateInsight gate={gate} />
        </article>
      ))}
    </div>
  );
}

function SummaryTiles({ analytics }: { analytics: LectureAnalyticsSummary }) {
  const attempts = analytics.quizzes.reduce((sum, quiz) => sum + quiz.total_attempts, 0);
  const correct = analytics.quizzes.reduce((sum, quiz) => sum + quiz.correct_attempts, 0);
  const learners = Math.max(0, ...analytics.quizzes.map((quiz) => quiz.unique_learners));
  const gateChecks = analytics.gates.reduce((sum, gate) => sum + gate.total_events, 0);
  return (
    <div className="analytics-kpis">
      <MetricCard label="Events" value={String(analytics.total_events)} />
      <MetricCard label="Quiz success" value={attempts ? percent(correct / attempts) : "n/a"} />
      <MetricCard label="Active learners" value={String(learners)} />
      <MetricCard label="Gate checks" value={String(gateChecks)} />
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="analytics-kpi">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function QuizInsight({ quiz }: { quiz: AnalyticsQuizMetric }) {
  return (
    <div className="analytics-insight-grid">
      <section>
        <h3>Answer distribution</h3>
        <MetricBars values={quiz.options.map((option) => ({
          label: `${String.fromCharCode(65 + option.option_index)} ${option.text}`,
          value: option.selections,
          total: quiz.total_attempts,
          tone: option.correct ? "correct" : "neutral",
        }))} />
      </section>
      <section>
        <h3>Attendance split</h3>
        <MetricBars values={splitBars(quiz.attendance_split)} />
      </section>
    </div>
  );
}

function GateInsight({ gate }: { gate: AnalyticsGateMetric }) {
  return (
    <div className="analytics-insight-grid">
      <section>
        <h3>Gate outcomes</h3>
        <MetricBars values={splitBars(gate.status_counts)} />
      </section>
      <section>
        <h3>Attendance split</h3>
        <MetricBars values={splitBars(gate.attendance_split)} />
      </section>
    </div>
  );
}

function MetricBars({
  values,
}: {
  values: Array<{ label: string; value: number; total: number; tone?: "correct" | "neutral" }>;
}) {
  return (
    <div className="metric-bar-list">
      {values.map((item) => (
        <div className={`metric-row is-${item.tone ?? "neutral"}`} key={item.label}>
          <div>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
          <div className="metric-track">
            <div className="metric-fill" style={barStyle(item.value, item.total)} />
          </div>
        </div>
      ))}
    </div>
  );
}

function splitBars(values: Record<string, number>) {
  const total = Object.values(values).reduce((sum, value) => sum + value, 0);
  return Object.entries(values).map(([label, value]) => ({
    label: label.replaceAll("_", " "),
    value,
    total,
  }));
}

function barStyle(value: number, total: number): CSSProperties {
  return { "--metric-width": `${total ? Math.round((value / total) * 100) : 0}%` } as CSSProperties;
}

function percent(value: number | null) {
  return value === null ? "n/a" : `${Math.round(value * 100)}%`;
}
