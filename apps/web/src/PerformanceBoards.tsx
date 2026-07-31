import { RefreshCw } from "lucide-react";

import { AnalyticsEmptyState } from "./AnalyticsEmptyState";
import { CoursePerformanceOverview } from "./CoursePerformanceOverview";
import { useI18n } from "./i18n";
import { PerformanceAnalysisWorkspace } from "./PerformanceAnalysisWorkspace";
import { PerformanceOverview } from "./PerformanceOverview";
import { lectureSnapshot } from "./performanceMetrics";
import type {
  CourseAnalyticsSummary,
  Lecture,
  LectureAnalyticsSummary,
  UniversityCourse,
} from "./types";

export function PerformancePageHeader({
  course,
  loading,
  refresh,
}: {
  course: UniversityCourse | null;
  loading: boolean;
  refresh: () => void;
}) {
  const { t } = useI18n();
  return (
    <section className="professor-page-header">
      <div>
        <h1>{t("professor.performance.title")}</h1>
        <p>{t("professor.performance.subtitle")}</p>
        {course ? (
          <div className="performance-course-context">
            <strong>{course.title}</strong>
            <span aria-hidden="true">·</span>
            <span>{course.term}</span>
          </div>
        ) : null}
      </div>
      <button
        aria-label={t("professor.refreshAnalytics")}
        className="refresh-button"
        disabled={loading || !course}
        type="button"
        onClick={refresh}
      >
        <RefreshCw className={loading ? "is-spinning" : ""} size={15} />
        <span>{loading ? t("professor.refreshing") : t("professor.refresh")}</span>
      </button>
    </section>
  );
}

export function PerformanceEmptyState() {
  const { t } = useI18n();
  return (
    <section className="performance-console is-empty">
      <div className="analytics-empty-state">
        <strong>{t("professor.noPublishedWorkspace")}</strong>
        <p>{t("professor.publishBeforeAnalytics")}</p>
      </div>
    </section>
  );
}

export function CourseBoard({
  analytics,
  error,
  lectures,
  loading,
  onSelectLecture,
}: {
  analytics: CourseAnalyticsSummary | null;
  error: string | null;
  lectures: Lecture[];
  loading: boolean;
  onSelectLecture: (lecture: Lecture) => void;
}) {
  const { t } = useI18n();
  return (
    <>
      <header className="analytics-board-heading">
        <div>
          <h2>{t("analytics.courseOverview")}</h2>
          <span>{t("analytics.courseOverviewHelp")}</span>
        </div>
        <div className="performance-course-meta">
          <span>{t("professor.publishedLectures", { count: lectures.length })}</span>
          {loading ? (
            <span className="analytics-loading" role="status">
              {t("professor.loadingAnalytics")}
            </span>
          ) : null}
        </div>
      </header>
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      {analytics ? (
        <CoursePerformanceOverview
          analytics={analytics}
          lectures={lectures}
          onSelectLecture={onSelectLecture}
        />
      ) : null}
    </>
  );
}

export function LectureBoard({
  analytics,
  error,
  lecture,
  lectureCount,
  loading,
}: {
  analytics: LectureAnalyticsSummary | null;
  error: string | null;
  lecture: Lecture;
  lectureCount: number;
  loading: boolean;
}) {
  const { t } = useI18n();
  const snapshot = lectureSnapshot(lecture, analytics);
  return (
    <>
      <header className="analytics-board-heading">
        <div className="selected-lecture-heading">
          <span className="selected-lecture-number">{lecture.number}</span>
          <div>
            <h2>{lecture.title}</h2>
            <span>{lecture.date}</span>
          </div>
        </div>
        <div className="performance-course-meta" aria-label={t("professor.analyticsStatus")}>
          <span>{t("professor.publishedLectures", { count: lectureCount })}</span>
          <span>{t("professor.eventsLoaded", { count: snapshot.events })}</span>
          {loading ? (
            <span className="analytics-loading" role="status">
              {t("professor.loadingAnalytics")}
            </span>
          ) : null}
        </div>
      </header>
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      <PerformanceOverview snapshot={snapshot} />
      {analytics?.total_events ? (
        <PerformanceAnalysisWorkspace analytics={analytics} />
      ) : (
        <AnalyticsEmptyState />
      )}
    </>
  );
}
