import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { AlertTriangle, BarChart3, CheckCircle2, RefreshCw, Users } from "lucide-react";

import { getLectureAnalytics } from "./analyticsApi";
import { AnalyticsChart } from "./PerformanceCharts";
import { lectureSnapshot, percent, splitBars } from "./performanceMetrics";
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
  publishedLectureIds,
  session,
}: {
  lectures: Lecture[];
  publishedLectureIds: string[];
  session: LoginSession;
}) {
  const course = session.courses.find((item) => item.id === demoPerformanceCourse.id) ?? demoPerformanceCourse;
  const published = new Set(publishedLectureIds);
  const visibleLectures = lectures.filter((lecture) => published.has(lecture.id));
  const [selectedLecture, setSelectedLecture] = useState<Lecture | null>(visibleLectures[2] ?? visibleLectures[0] ?? null);
  const [analytics, setAnalytics] = useState<LectureAnalyticsSummary | null>(null);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedLecture) return;
    void refreshAnalytics(selectedLecture);
    // Run once for the initially selected lecture.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!visibleLectures.length) {
      setSelectedLecture(null);
      setAnalytics(null);
      return;
    }
    if (!selectedLecture || !visibleLectures.some((lecture) => lecture.id === selectedLecture.id)) {
      setSelectedLecture(visibleLectures[0]);
      setAnalytics(null);
    }
  }, [selectedLecture, visibleLectures]);

  async function refreshAnalytics(lecture = selectedLecture) {
    if (!lecture) return;
    setAnalyticsError(null);
    setSelectedLecture(lecture);
    setLoading(true);
    try {
      setAnalytics(await getLectureAnalytics(course.id, lecture.id, session));
    } catch (error) {
      setAnalyticsError(error instanceof Error ? error.message : "Lecture analytics loading failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="professor-screen performance-page">
      <section className="professor-page-header">
        <div>
          <h1>Course performance</h1>
          <p>Lecture-level learning signals from published tutor workspaces.</p>
        </div>
        <button
          aria-label="Refresh analytics"
          className="refresh-button"
          disabled={loading || !selectedLecture}
          type="button"
          onClick={() => void refreshAnalytics()}
        >
          <RefreshCw className={loading ? "is-spinning" : ""} size={15} />
          <span>{loading ? "Refreshing" : "Refresh"}</span>
        </button>
      </section>

      {!selectedLecture ? (
        <section className="performance-console is-empty">
          <div className="analytics-empty-state">
            <strong>No published course workspace yet</strong>
            <p>Create and publish a tutor workspace before course analytics appear here.</p>
          </div>
        </section>
      ) : (

      <section className="performance-console" aria-labelledby="course-performance-title">
        <header className="performance-course-header">
          <div>
            <h2 id="course-performance-title">{course.title}</h2>
            <p>{course.professor} · {course.term}</p>
          </div>
          <div className="performance-course-meta" aria-label="Course analytics status">
            <span>{visibleLectures.length} published lectures</span>
            <span>{lectureSnapshot(selectedLecture, analytics).events} events loaded</span>
          </div>
        </header>

        <div className="performance-workbench">
          <nav className="performance-lecture-rail" aria-label="Performance lecture list">
            <div className="performance-rail-heading">
              <span>Course lectures</span>
              <small>Published tutor workspaces only</small>
            </div>
            <div className="performance-lecture-scroll">
              {visibleLectures.map((lecture) => (
                <LectureRow
                  active={lecture.id === selectedLecture.id}
                  key={lecture.id}
                  lecture={lecture}
                  onSelect={() => void refreshAnalytics(lecture)}
                />
              ))}
            </div>
          </nav>

          <section className="analytics-board" aria-live="polite">
            <header className="analytics-board-heading">
              <div>
                <p>Lecture {selectedLecture.number}</p>
                <h2>{selectedLecture.title}</h2>
                <span>{selectedLecture.date}</span>
              </div>
              {loading ? <span className="analytics-loading">Loading analytics</span> : null}
            </header>
            {analyticsError ? <p className="form-error">{analyticsError}</p> : null}
            <PerformanceOverview snapshot={lectureSnapshot(selectedLecture, analytics)} />
            {analytics ? <AnalyticsChart analytics={analytics} /> : null}
            {analytics ? <AnalyticsSummary analytics={analytics} /> : <AnalyticsEmptyState />}
          </section>
        </div>
      </section>
      )}
    </main>
  );
}

function LectureRow({
  active,
  lecture,
  onSelect,
}: {
  active: boolean;
  lecture: Lecture;
  onSelect: () => void;
}) {
  const snapshot = lectureSnapshot(lecture, null);
  return (
    <button className={active ? "is-active" : undefined} type="button" onClick={onSelect}>
      <span className="lecture-index">{lecture.number}</span>
      <span className="lecture-row-body">
        <strong>{lecture.title}</strong>
        <small>{lecture.date}</small>
        <span className="lecture-row-metrics">
          <span>{snapshot.learners} learners</span>
          <span>{snapshot.quizRate} quiz</span>
          <span>{snapshot.gateRate} gates</span>
        </span>
      </span>
      <span className={`lecture-status is-${snapshot.status}`} />
    </button>
  );
}

function PerformanceOverview({ snapshot }: { snapshot: ReturnType<typeof lectureSnapshot> }) {
  return (
    <div className="performance-overview" aria-label="Selected lecture performance overview">
      <MetricCard icon={<BarChart3 size={18} />} label="Events" value={String(snapshot.events)} />
      <MetricCard icon={<CheckCircle2 size={18} />} label="Quiz success" value={snapshot.quizRate} />
      <MetricCard icon={<Users size={18} />} label="Active learners" value={String(snapshot.learners)} />
      <MetricCard icon={<AlertTriangle size={18} />} label="Gate pass rate" value={snapshot.gateRate} />
    </div>
  );
}

function AnalyticsSummary({ analytics }: { analytics: LectureAnalyticsSummary }) {
  if (!analytics.total_events) return <AnalyticsEmptyState />;
  return (
    <div className="analytics-summary">
      <section className="analytics-column" aria-label="Quiz insights">
        <h3>Quiz friction</h3>
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
      </section>
      <section className="analytics-column" aria-label="Quality gate insights">
        <h3>Gate evidence</h3>
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
      </section>
    </div>
  );
}

function MetricCard({ icon, label, value }: { icon?: ReactNode; label: string; value: string }) {
  return (
    <div className="analytics-kpi">
      <span>{icon}{label}</span>
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
          tone: option.correct ? "correct" : "wrong",
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
  values: Array<{ label: string; value: number; total: number; tone?: "correct" | "neutral" | "wrong" }>;
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

function AnalyticsEmptyState() {
  return (
    <div className="analytics-empty-state">
      <strong>No learner signals yet</strong>
      <p>Publish the workspace and ask students to answer quizzes or quality gates.</p>
    </div>
  );
}

function barStyle(value: number, total: number): CSSProperties {
  return { "--metric-width": `${total ? Math.round((value / total) * 100) : 0}%` } as CSSProperties;
}
