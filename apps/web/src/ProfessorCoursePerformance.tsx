import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LayoutDashboard } from "lucide-react";

import { getCourseAnalytics, getLectureAnalytics } from "./analyticsApi";
import { useI18n } from "./i18n";
import {
  CourseBoard,
  LectureBoard,
  PerformanceEmptyState,
  PerformancePageHeader,
} from "./PerformanceBoards";
import { PerformanceLectureRow } from "./PerformanceLectureRow";
import { courseLectureSnapshot, lectureSnapshot } from "./performanceMetrics";
import { performanceCourseOptions, ProfessorCourseTabs } from "./ProfessorCourseTabs";
import type {
  CourseAnalyticsSummary,
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
  const courseOptions = useMemo(
    () => performanceCourseOptions([], workspaceCourse, publishedLectureIds.length > 0),
    [publishedLectureIds.length, workspaceCourse],
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
  const [courseAnalytics, setCourseAnalytics] = useState<CourseAnalyticsSummary | null>(null);
  const [lectureAnalytics, setLectureAnalytics] = useState<LectureAnalyticsSummary | null>(null);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const requestVersion = useRef(0);

  const loadCourseAnalytics = useCallback(async () => {
    if (!course || !workspaceSelected) return;
    const version = ++requestVersion.current;
    setAnalyticsError(null);
    setLoading(true);
    try {
      const summary = await getCourseAnalytics(course.id, session);
      if (version === requestVersion.current) setCourseAnalytics(summary);
    } catch (error) {
      if (version === requestVersion.current) setAnalyticsError(errorMessage(error, "course"));
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }, [course, session, workspaceSelected]);

  const loadLectureAnalytics = useCallback(
    async (lecture: Lecture) => {
      if (!course || !workspaceSelected) return;
      const version = ++requestVersion.current;
      setAnalyticsError(null);
      setSelectedLecture(lecture);
      setLectureAnalytics((current) => (current?.lecture_id === lecture.id ? current : null));
      setLoading(true);
      try {
        const summary = await getLectureAnalytics(course.id, lecture.id, session);
        if (version === requestVersion.current) setLectureAnalytics(summary);
      } catch (error) {
        if (version === requestVersion.current) setAnalyticsError(errorMessage(error, "lecture"));
      } finally {
        if (version === requestVersion.current) setLoading(false);
      }
    },
    [course, session, workspaceSelected],
  );

  useEffect(() => setSelectedCourseId(workspaceCourse.id), [workspaceCourse.id]);

  useEffect(() => {
    requestVersion.current += 1;
    setSelectedLecture(null);
    setCourseAnalytics(null);
    setLectureAnalytics(null);
    setAnalyticsError(null);
  }, [selectedCourseId]);

  useEffect(() => {
    if (visibleLectures.length) void loadCourseAnalytics();
  }, [loadCourseAnalytics, visibleLectures.length]);

  const showOverview = () => {
    requestVersion.current += 1;
    setSelectedLecture(null);
    setLectureAnalytics(null);
    setAnalyticsError(null);
    if (!courseAnalytics) void loadCourseAnalytics();
  };
  const selectedAnalytics =
    lectureAnalytics?.lecture_id === selectedLecture?.id ? lectureAnalytics : null;

  return (
    <main className="professor-screen performance-page" data-tour="course-performance-workflow">
      <PerformancePageHeader
        course={course}
        loading={loading}
        refresh={() =>
          selectedLecture ? void loadLectureAnalytics(selectedLecture) : void loadCourseAnalytics()
        }
      />
      {courseOptions.length > 1 ? (
        <ProfessorCourseTabs
          courses={courseOptions}
          publishedLectureCount={visibleLectures.length}
          selectedCourseId={selectedCourseId}
          workspaceCourseId={workspaceCourse.id}
          onSelect={setSelectedCourseId}
        />
      ) : null}
      {!course || !visibleLectures.length ? (
        <PerformanceEmptyState />
      ) : (
        <section className="performance-console">
          <nav className="performance-lecture-rail" aria-label={t("professor.lectureList")}>
            <div className="performance-rail-heading">
              <span>{t("professor.courseLectures")}</span>
              <small>{t("professor.publishedOnly")}</small>
            </div>
            <button
              aria-current={!selectedLecture ? "true" : undefined}
              aria-pressed={!selectedLecture}
              className={`course-overview-row${!selectedLecture ? " is-active" : ""}`}
              type="button"
              onClick={showOverview}
            >
              <span className="lecture-index course-overview-icon">
                <LayoutDashboard size={16} />
              </span>
              <span className="lecture-row-body">
                <strong>{t("analytics.courseOverview")}</strong>
                <small>{t("analytics.allPublishedLectures")}</small>
              </span>
            </button>
            <div className="performance-lecture-scroll">
              {visibleLectures.map((lecture) => (
                <PerformanceLectureRow
                  active={lecture.id === selectedLecture?.id}
                  key={lecture.id}
                  lecture={lecture}
                  onSelect={() => void loadLectureAnalytics(lecture)}
                  snapshot={snapshotFor(lecture, selectedAnalytics, courseAnalytics)}
                />
              ))}
            </div>
          </nav>
          <section className="analytics-board" aria-busy={loading}>
            {selectedLecture ? (
              <LectureBoard
                analytics={selectedAnalytics}
                error={analyticsError}
                lecture={selectedLecture}
                lectureCount={visibleLectures.length}
                loading={loading}
              />
            ) : (
              <CourseBoard
                analytics={courseAnalytics}
                error={analyticsError}
                lectures={visibleLectures}
                loading={loading}
                onSelectLecture={(lecture) => void loadLectureAnalytics(lecture)}
              />
            )}
          </section>
        </section>
      )}
    </main>
  );
}

function snapshotFor(
  lecture: Lecture,
  selected: LectureAnalyticsSummary | null,
  course: CourseAnalyticsSummary | null,
) {
  if (selected?.lecture_id === lecture.id) return lectureSnapshot(lecture, selected);
  const rollup = course?.lectures.find((item) => item.lecture_id === lecture.id);
  return rollup ? courseLectureSnapshot(rollup) : null;
}

function errorMessage(error: unknown, scope: "course" | "lecture") {
  return error instanceof Error
    ? error.message
    : `${scope === "course" ? "Course" : "Lecture"} analytics loading failed.`;
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
