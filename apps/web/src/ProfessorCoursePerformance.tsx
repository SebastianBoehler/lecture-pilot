import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { RefreshCw } from "lucide-react";

import { AnalyticsEmptyState } from "./AnalyticsEmptyState";
import { getLectureAnalytics } from "./analyticsApi";
import { useI18n } from "./i18n";
import { AnalyticsChart } from "./PerformanceCharts";
import { PerformanceLectureRow } from "./PerformanceLectureRow";
import { PerformanceOverview } from "./PerformanceOverview";
import { lectureSnapshot, percent, splitBars } from "./performanceMetrics";
import { performanceCourseOptions, ProfessorCourseTabs } from "./ProfessorCourseTabs";
import { ProfessorLearningMapTree } from "./ProfessorLearningMapTree";
import type {
  AnalyticsGateMetric,
  AnalyticsQuizMetric,
  Lecture,
  LectureAnalyticsSummary,
  LoginSession,
  UniversityCourse,
} from "./types";

export function ProfessorCoursePerformance({
  lectures,
  publishedLectureIds,
  session,
  workspaceCourse,
}: {
  lectures: Lecture[];
  publishedLectureIds: string[];
  session: LoginSession;
  workspaceCourse: UniversityCourse;
}) {
  const { t } = useI18n();
  const hasPublishedWorkspace = publishedLectureIds.length > 0;
  const courseOptions = useMemo(
    () => performanceCourseOptions([], workspaceCourse, hasPublishedWorkspace),
    [hasPublishedWorkspace, workspaceCourse],
  );
  const [selectedCourseId, setSelectedCourseId] = useState(workspaceCourse.id);
  const course =
    courseOptions.find((item) => item.id === selectedCourseId) ?? courseOptions[0] ?? null;
  const workspaceSelected = Boolean(course && isWorkspaceCourse(course, workspaceCourse));
  const visibleLectures = useMemo(() => {
    if (!workspaceSelected) return [];
    const published = new Set(publishedLectureIds);
    return lectures.filter((lecture) => published.has(lecture.id));
  }, [lectures, publishedLectureIds, workspaceSelected]);
  const [selectedLecture, setSelectedLecture] = useState<Lecture | null>(null);
  const [analytics, setAnalytics] = useState<LectureAnalyticsSummary | null>(null);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setSelectedCourseId(workspaceCourse.id);
  }, [workspaceCourse.id]);

  useEffect(() => {
    setSelectedLecture(null);
    setAnalytics(null);
    setAnalyticsError(null);
  }, [selectedCourseId]);

  useEffect(() => {
    if (!visibleLectures.length) {
      setSelectedLecture(null);
      setAnalytics(null);
      return;
    }
    if (!selectedLecture) {
      void refreshAnalytics(visibleLectures[2] ?? visibleLectures[0]);
    }
  }, [selectedLecture, visibleLectures]);

  async function refreshAnalytics(lecture = selectedLecture) {
    if (!lecture || !course || !workspaceSelected) return;
    setAnalyticsError(null);
    setSelectedLecture(lecture);
    setLoading(true);
    try {
      setAnalytics(await getLectureAnalytics(course.id, lecture.id, session));
    } catch (error) {
      setAnalyticsError(
        error instanceof Error ? error.message : "Lecture analytics loading failed.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="professor-screen performance-page">
      <section className="professor-page-header">
        <div>
          <h1>{t("professor.performance.title")}</h1>
          <p>{t("professor.performance.subtitle")}</p>
        </div>
        <button
          aria-label={t("professor.refreshAnalytics")}
          className="refresh-button"
          disabled={loading || !selectedLecture}
          type="button"
          onClick={() => void refreshAnalytics()}
        >
          <RefreshCw className={loading ? "is-spinning" : ""} size={15} />
          <span>{loading ? t("professor.refreshing") : t("professor.refresh")}</span>
        </button>
      </section>

      {courseOptions.length ? (
        <ProfessorCourseTabs
          courses={courseOptions}
          publishedLectureCount={visibleLectures.length}
          selectedCourseId={selectedCourseId}
          workspaceCourseId={workspaceCourse.id}
          onSelect={setSelectedCourseId}
        />
      ) : null}

      {!selectedLecture || !course ? (
        <section className="performance-console is-empty">
          <div className="analytics-empty-state">
            <strong>{t("professor.noPublishedWorkspace")}</strong>
            <p>{t("professor.publishBeforeAnalytics")}</p>
          </div>
        </section>
      ) : (
        <section className="performance-console" aria-labelledby="course-performance-title">
          <header className="performance-course-header">
            <div>
              <h2 id="course-performance-title">{course.title}</h2>
              <p>
                {course.professor} · {course.term}
              </p>
            </div>
            <div className="performance-course-meta" aria-label={t("professor.analyticsStatus")}>
              <span>{t("professor.publishedLectures", { count: visibleLectures.length })}</span>
              <span>
                {t("professor.eventsLoaded", {
                  count: lectureSnapshot(selectedLecture, analytics).events,
                })}
              </span>
            </div>
          </header>

          <div className="performance-workbench">
            <nav className="performance-lecture-rail" aria-label={t("professor.lectureList")}>
              <div className="performance-rail-heading">
                <span>{t("professor.courseLectures")}</span>
                <small>{t("professor.publishedOnly")}</small>
              </div>
              <div className="performance-lecture-scroll">
                {visibleLectures.map((lecture) => (
                  <PerformanceLectureRow
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
                {loading ? (
                  <span className="analytics-loading">{t("professor.loadingAnalytics")}</span>
                ) : null}
              </header>
              {analyticsError ? <p className="form-error">{analyticsError}</p> : null}
              <PerformanceOverview snapshot={lectureSnapshot(selectedLecture, analytics)} />
              {analytics ? <ProfessorLearningMapTree analytics={analytics} /> : null}
              {analytics ? <AnalyticsChart analytics={analytics} /> : null}
              {analytics ? <AnalyticsSummary analytics={analytics} /> : <AnalyticsEmptyState />}
            </section>
          </div>
        </section>
      )}
    </main>
  );
}

function isWorkspaceCourse(course: UniversityCourse, workspaceCourse: UniversityCourse) {
  return (
    course.id === workspaceCourse.id ||
    normalizeCourseTitle(course.title) === normalizeCourseTitle(workspaceCourse.title)
  );
}

function normalizeCourseTitle(title: string) {
  return title.toLowerCase().replace(/\s+/g, " ").trim();
}

function AnalyticsSummary({ analytics }: { analytics: LectureAnalyticsSummary }) {
  const { t } = useI18n();
  if (!analytics.total_events) return <AnalyticsEmptyState />;
  return (
    <div className="analytics-summary">
      <section className="analytics-column" aria-label={t("analytics.quizInsights")}>
        <h3>{t("analytics.quizFriction")}</h3>
        {analytics.quizzes.map((quiz) => (
          <article className="analytics-panel" key={quiz.component_id}>
            <header>
              <span>Quiz</span>
              <strong>{quiz.title}</strong>
              <small>
                {t("analytics.correct", {
                  count: quiz.unique_learners,
                  rate: percent(quiz.correct_rate),
                })}
              </small>
            </header>
            <p>{quiz.question}</p>
            <QuizInsight quiz={quiz} />
          </article>
        ))}
      </section>
      <section className="analytics-column" aria-label={t("analytics.gateInsights")}>
        <h3>{t("analytics.gateEvidence")}</h3>
        {analytics.gates.map((gate) => (
          <article className="analytics-panel" key={gate.gate_id}>
            <header>
              <span>Gate</span>
              <strong>{gate.gate_id}</strong>
              <small>
                {t("analytics.checksLearners", {
                  checks: gate.total_events,
                  learners: gate.unique_learners,
                })}
              </small>
            </header>
            <GateInsight gate={gate} />
          </article>
        ))}
      </section>
    </div>
  );
}

function QuizInsight({ quiz }: { quiz: AnalyticsQuizMetric }) {
  const { t } = useI18n();
  return (
    <div className="analytics-insight-grid">
      <section>
        <h3>{t("analytics.answerDistribution")}</h3>
        <MetricBars
          values={quiz.options.map((option) => ({
            label: `${String.fromCharCode(65 + option.option_index)} ${option.text}`,
            value: option.selections,
            total: quiz.total_attempts,
            tone: option.correct ? "correct" : "wrong",
          }))}
        />
      </section>
      <section>
        <h3>{t("analytics.attendanceSplit")}</h3>
        <MetricBars values={splitBars(quiz.attendance_split)} />
      </section>
    </div>
  );
}

function GateInsight({ gate }: { gate: AnalyticsGateMetric }) {
  const { t } = useI18n();
  return (
    <div className="analytics-insight-grid">
      <section>
        <h3>{t("analytics.gateOutcomes")}</h3>
        <MetricBars values={splitBars(gate.status_counts)} />
      </section>
      <section>
        <h3>{t("analytics.attendanceSplit")}</h3>
        <MetricBars values={splitBars(gate.attendance_split)} />
      </section>
    </div>
  );
}

function MetricBars({
  values,
}: {
  values: Array<{
    label: string;
    value: number;
    total: number;
    tone?: "correct" | "neutral" | "wrong";
  }>;
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

function barStyle(value: number, total: number): CSSProperties {
  return { "--metric-width": `${total ? Math.round((value / total) * 100) : 0}%` } as CSSProperties;
}
