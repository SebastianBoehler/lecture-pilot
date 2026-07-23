import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";

import { AnalyticsEmptyState } from "./AnalyticsEmptyState";
import { getLectureAnalytics } from "./analyticsApi";
import { useI18n } from "./i18n";
import { AnalyticsChart } from "./PerformanceCharts";
import { PerformanceInsights } from "./PerformanceInsights";
import { PerformanceLectureRow } from "./PerformanceLectureRow";
import { PerformanceOverview } from "./PerformanceOverview";
import { lectureSnapshot } from "./performanceMetrics";
import { performanceCourseOptions, ProfessorCourseTabs } from "./ProfessorCourseTabs";
import { ProfessorLearningMapTree } from "./ProfessorLearningMapTree";
import type { Lecture, LectureAnalyticsSummary, LoginSession, UniversityCourse } from "./types";

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
  const analyticsRequestVersion = useRef(0);

  useEffect(() => {
    setSelectedCourseId(workspaceCourse.id);
  }, [workspaceCourse.id]);

  useEffect(() => {
    analyticsRequestVersion.current += 1;
    setSelectedLecture(null);
    setAnalytics(null);
    setAnalyticsError(null);
  }, [selectedCourseId]);

  const refreshAnalytics = useCallback(
    async (lecture = selectedLecture) => {
      if (!lecture || !course || !workspaceSelected) return;
      const requestVersion = ++analyticsRequestVersion.current;
      setAnalyticsError(null);
      setSelectedLecture(lecture);
      setAnalytics((current) => (current?.lecture_id === lecture.id ? current : null));
      setLoading(true);
      try {
        const summary = await getLectureAnalytics(course.id, lecture.id, session);
        if (requestVersion !== analyticsRequestVersion.current) return;
        setAnalytics(summary);
      } catch (error) {
        if (requestVersion !== analyticsRequestVersion.current) return;
        setAnalyticsError(
          error instanceof Error ? error.message : "Lecture analytics loading failed.",
        );
      } finally {
        if (requestVersion === analyticsRequestVersion.current) setLoading(false);
      }
    },
    [course, selectedLecture, session, workspaceSelected],
  );

  useEffect(() => {
    if (!visibleLectures.length) {
      setSelectedLecture(null);
      setAnalytics(null);
      return;
    }
    if (!selectedLecture) {
      void refreshAnalytics(visibleLectures[0]);
    }
  }, [refreshAnalytics, selectedLecture, visibleLectures]);

  const selectedAnalytics = analytics?.lecture_id === selectedLecture?.id ? analytics : null;

  return (
    <main className="professor-screen performance-page" data-tour="course-performance-workflow">
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
          disabled={loading || !selectedLecture}
          type="button"
          onClick={() => void refreshAnalytics()}
        >
          <RefreshCw className={loading ? "is-spinning" : ""} size={15} />
          <span>{loading ? t("professor.refreshing") : t("professor.refresh")}</span>
        </button>
      </section>

      {courseOptions.length > 1 ? (
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
        <section className="performance-console">
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
                  snapshot={
                    lecture.id === selectedLecture.id
                      ? lectureSnapshot(lecture, selectedAnalytics)
                      : null
                  }
                />
              ))}
            </div>
          </nav>

          <section className="analytics-board" aria-busy={loading}>
            <header className="analytics-board-heading">
              <div>
                <h2>{selectedLecture.title}</h2>
                <span>{selectedLecture.date}</span>
              </div>
              <div className="performance-course-meta" aria-label={t("professor.analyticsStatus")}>
                <span>{t("professor.publishedLectures", { count: visibleLectures.length })}</span>
                <span>
                  {t("professor.eventsLoaded", {
                    count: lectureSnapshot(selectedLecture, selectedAnalytics).events,
                  })}
                </span>
                {loading ? (
                  <span className="analytics-loading" role="status">
                    {t("professor.loadingAnalytics")}
                  </span>
                ) : null}
              </div>
            </header>
            {analyticsError ? (
              <p className="form-error" role="alert">
                {analyticsError}
              </p>
            ) : null}
            <PerformanceOverview snapshot={lectureSnapshot(selectedLecture, selectedAnalytics)} />
            {selectedAnalytics?.total_events ? (
              <>
                <div className="performance-evidence-layout">
                  <ProfessorLearningMapTree analytics={selectedAnalytics} />
                  <PerformanceInsights analytics={selectedAnalytics} />
                </div>
                <AnalyticsChart analytics={selectedAnalytics} />
              </>
            ) : (
              <AnalyticsEmptyState />
            )}
          </section>
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
