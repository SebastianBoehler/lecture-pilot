import { useState } from "react";

import {
  availableCourseLectures,
  buildCourseGroups,
  publishedCourseLectures,
} from "./dashboardCourses";
import { DashboardLectureRow } from "./DashboardLectureRow";
import { useI18n } from "./i18n";
import type { Attendance, Lecture, LoginSession, UniversityCourse } from "./types";
import { ExamReadinessPanel } from "./ExamReadinessPanel";
import { LearnerOnboarding } from "./LearnerOnboarding";
import { NextStudyRecommendation } from "./NextStudyRecommendation";
import { CourseSyncEmpty, CourseSyncSkeleton } from "./CourseSyncState";
import type { LearnerProfileState } from "./useLearnerProfile";

const LECTURE_PREVIEW_COUNT = 2;

export function Dashboard({
  lectures,
  publishedLectureIds,
  session,
  workspaceCourse,
  learnerProfileState,
  onOpen,
  onSetAttendance,
}: {
  lectures: Lecture[];
  publishedLectureIds: string[];
  session: LoginSession | null;
  workspaceCourse: UniversityCourse;
  learnerProfileState?: LearnerProfileState;
  onOpen: (lecture: Lecture) => void;
  onSetAttendance: (lectureId: string, attendance: Attendance) => void;
}) {
  const { t } = useI18n();
  const studentName = session?.display_name?.trim();
  const syncStatus = session?.university_course_sync_status ?? "ready";
  const courseGroups = buildCourseGroups(session, workspaceCourse, lectures, publishedLectureIds, {
    aiTutorAvailable: t("dashboard.aiTutorAvailable"),
    noTutor: t("dashboard.noTutor"),
  });
  const visibleCourseGroups = syncStatus === "loading" ? [] : courseGroups;
  const [openCourses, setOpenCourses] = useState<Record<string, boolean>>({});
  const [expandedLectureLists, setExpandedLectureLists] = useState<Record<string, boolean>>({});
  const workspaceLectures = availableCourseLectures(
    publishedCourseLectures(lectures, publishedLectureIds),
  );
  const courseProfile = learnerProfileState?.profile?.courses?.find(
    (course) => course.course_id === workspaceCourse.id,
  );

  return (
    <main className="dashboard">
      <section className="dashboard-header">
        <h1>
          {studentName
            ? t("dashboard.welcomeNamed", { student: studentName })
            : t("dashboard.welcome")}
        </h1>
        <p>{t("dashboard.subtitle")}</p>
      </section>

      <NextStudyRecommendation
        lectures={workspaceLectures}
        passedLectureIds={courseProfile?.passed_lecture_ids ?? []}
        onOpen={onOpen}
      />

      <section className="course-panel" aria-labelledby="course-workspaces">
        <div className="panel-heading">
          <h2 id="course-workspaces">{t("dashboard.courseWorkspaces")}</h2>
        </div>
        <div className="course-workspace-list">
          {syncStatus === "loading" ? <CourseSyncSkeleton /> : null}
          {syncStatus !== "loading" && courseGroups.length === 0 ? (
            <CourseSyncEmpty failed={syncStatus === "error"} />
          ) : null}
          {visibleCourseGroups.map((group) => {
            const { course, sources, status, statusLabel, tutorAvailable, courseLectures } = group;
            const courseOpen = openCourses[course.id] ?? tutorAvailable;
            const allLecturesShown = expandedLectureLists[course.id] ?? false;
            const visibleLectures = allLecturesShown
              ? courseLectures
              : courseLectures.slice(0, LECTURE_PREVIEW_COUNT);
            const bodyId = `course-workspace-${course.id}`;
            return (
              <article className={`course-workspace is-${status}`} key={`${status}-${course.id}`}>
                <div className="course-row">
                  <div>
                    <div className="course-title-line">
                      <h3>{course.title}</h3>
                      {sources.length ? (
                        <span aria-label="Course sources" className="course-source-tags">
                          {sources.map((source) => (
                            <span className="course-source-tag" key={source}>
                              {source === "alma" ? "Alma" : "ILIAS"}
                            </span>
                          ))}
                        </span>
                      ) : null}
                    </div>
                    {tutorAvailable ? <p>{course.professor}</p> : null}
                  </div>
                  <div className="course-row-actions">
                    <span className={`workspace-status is-${status}`}>{statusLabel}</span>
                    {tutorAvailable ? (
                      <button
                        aria-controls={bodyId}
                        aria-expanded={courseOpen}
                        className="course-toggle"
                        type="button"
                        onClick={() =>
                          setOpenCourses((current) => ({ ...current, [course.id]: !courseOpen }))
                        }
                      >
                        {courseOpen
                          ? t("dashboard.hideLectures")
                          : t("dashboard.showLectures", { count: courseLectures.length })}
                      </button>
                    ) : null}
                  </div>
                </div>
                {tutorAvailable ? (
                  <div className="course-workspace-body" hidden={!courseOpen} id={bodyId}>
                    <div
                      className="lecture-list"
                      aria-label={t("dashboard.availableLectures", { course: course.title })}
                    >
                      {visibleLectures.map((lecture) => (
                        <DashboardLectureRow
                          key={lecture.id}
                          lecture={lecture}
                          onOpen={onOpen}
                          onSetAttendance={onSetAttendance}
                        />
                      ))}
                    </div>
                    {courseLectures.length > LECTURE_PREVIEW_COUNT ? (
                      <button
                        className="lecture-list-toggle"
                        type="button"
                        onClick={() =>
                          setExpandedLectureLists((current) => ({
                            ...current,
                            [course.id]: !allLecturesShown,
                          }))
                        }
                      >
                        {allLecturesShown
                          ? t("dashboard.showFirstLectures", { count: LECTURE_PREVIEW_COUNT })
                          : t("dashboard.showAllLectures", { count: courseLectures.length })}
                      </button>
                    ) : null}
                    <ExamReadinessPanel
                      course={course}
                      lectures={availableCourseLectures(courseLectures)}
                      session={session}
                      onOpenLecture={onOpen}
                    />
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      </section>
      {learnerProfileState?.profile && !learnerProfileState.profile.onboarding_completed ? (
        <LearnerOnboarding onComplete={learnerProfileState.saveCalibration} />
      ) : null}
    </main>
  );
}
