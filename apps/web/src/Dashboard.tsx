import { useState } from "react";

import { buildCourseGroups, publishedCourseLectures } from "./dashboardCourses";
import { useI18n } from "./i18n";
import type { Attendance, Lecture, LoginSession, UniversityCourse } from "./types";
import { ExamReadinessPanel } from "./ExamReadinessPanel";
import { LearnerOnboarding } from "./LearnerOnboarding";
import { NextStudyRecommendation } from "./NextStudyRecommendation";
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
  const studentLabel = session?.email ?? session?.username ?? "student";
  const courseGroups = buildCourseGroups(session, workspaceCourse, lectures, publishedLectureIds, {
    aiTutorAvailable: t("dashboard.aiTutorAvailable"),
    noMatchedTutor: t("dashboard.noMatchedTutor"),
    noTutor: t("dashboard.noTutor"),
    publishToEnable: t("dashboard.publishToEnable"),
  });
  const [openCourses, setOpenCourses] = useState<Record<string, boolean>>({});
  const [expandedLectureLists, setExpandedLectureLists] = useState<Record<string, boolean>>({});
  const workspaceLectures = publishedCourseLectures(lectures, publishedLectureIds);
  const courseProfile = learnerProfileState?.profile?.courses?.find(
    (course) => course.course_id === workspaceCourse.id,
  );

  return (
    <main className="dashboard">
      <section className="dashboard-header">
        <h1>{t("dashboard.welcome", { student: studentLabel })}</h1>
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
          {courseGroups.map((group) => {
            const { course, status, statusLabel, emptyText, tutorAvailable, courseLectures } =
              group;
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
                    <h3>{course.title}</h3>
                    <p>{course.professor}</p>
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
                        <article className="lecture-row" key={lecture.id}>
                          <div className="lecture-number">{lecture.number}</div>
                          <div>
                            <h3>{lecture.title}</h3>
                            <p>
                              {lecture.date} ·{" "}
                              {t("dashboard.attendance", {
                                status: attendanceLabel(lecture.attendance, t),
                              })}
                            </p>
                            <div
                              className="attendance-control"
                              aria-label={t("dashboard.attendanceFor", {
                                lecture: lecture.title,
                              })}
                            >
                              {(["present", "absent", "unknown"] as const).map((status) => (
                                <button
                                  aria-pressed={lecture.attendance === status}
                                  className={
                                    lecture.attendance === status ? "is-active" : undefined
                                  }
                                  key={status}
                                  onClick={() => onSetAttendance(lecture.id, status)}
                                  type="button"
                                >
                                  {attendanceLabel(status, t)}
                                </button>
                              ))}
                            </div>
                          </div>
                          <button type="button" onClick={() => onOpen(lecture)}>
                            {t("dashboard.openLecture", { number: lecture.number })}
                          </button>
                        </article>
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
                      lectures={courseLectures}
                      session={session}
                      onOpenLecture={onOpen}
                    />
                  </div>
                ) : (
                  <p className="workspace-empty">{emptyText}</p>
                )}
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

function attendanceLabel(
  status: Attendance,
  t: (key: "attendance.present" | "attendance.absent" | "attendance.unknown") => string,
) {
  if (status === "present") return t("attendance.present");
  if (status === "absent") return t("attendance.absent");
  return t("attendance.unknown");
}
