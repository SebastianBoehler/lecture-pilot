import { useState } from "react";

import { useI18n } from "./i18n";
import type { Attendance, Lecture, LoginSession, UniversityCourse } from "./types";
import { readDemoWorkspaceCourse } from "./demoWorkspaceAccess";
import { hasDevelopmentWorkspaceAccess } from "./devWorkspaceAccess";
import { ExamReadinessPanel } from "./ExamReadinessPanel";

const LECTURE_PREVIEW_COUNT = 2;

type CourseWorkspaceStatus = "matched" | "unmatched";

type CourseWorkspaceGroup = {
  course: UniversityCourse;
  status: CourseWorkspaceStatus;
  statusLabel: string;
  emptyText: string;
  tutorAvailable: boolean;
  courseLectures: Lecture[];
};

export function Dashboard({
  lectures,
  publishedLectureIds,
  session,
  workspaceCourse,
  onOpen,
  onSetAttendance,
}: {
  lectures: Lecture[];
  publishedLectureIds: string[];
  session: LoginSession | null;
  workspaceCourse: UniversityCourse;
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

  return (
    <main className="dashboard">
      <section className="dashboard-header">
        <h1>{t("dashboard.welcome", { student: studentLabel })}</h1>
        <p>{t("dashboard.subtitle")}</p>
      </section>

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
    </main>
  );
}

function buildCourseGroups(
  session: LoginSession | null,
  workspaceCourse: UniversityCourse,
  lectures: Lecture[],
  publishedLectureIds: string[],
  labels: {
    aiTutorAvailable: string;
    noMatchedTutor: string;
    noTutor: string;
    publishToEnable: string;
  },
): CourseWorkspaceGroup[] {
  const enrolledCourses = session?.courses ?? [];
  const courseGroups = enrolledCourses.length
    ? enrolledCourses.map((course) =>
        buildEnrolledCourseGroup(course, workspaceCourse, lectures, publishedLectureIds, labels),
      )
    : hasWorkspaceAccess(workspaceCourse)
      ? [buildDiscoverableCourseGroup(workspaceCourse, lectures, publishedLectureIds, labels)]
      : [];

  if (
    enrolledCourses.length &&
    !enrolledCourses.some((course) => isWorkspaceCourse(course, workspaceCourse))
  ) {
    if (hasWorkspaceAccess(workspaceCourse) && publishedLectureIds.length > 0) {
      courseGroups.push(
        buildDiscoverableCourseGroup(workspaceCourse, lectures, publishedLectureIds, labels),
      );
    }
  }

  return courseGroups;
}

function buildEnrolledCourseGroup(
  course: UniversityCourse,
  workspaceCourse: UniversityCourse,
  lectures: Lecture[],
  publishedLectureIds: string[],
  labels: {
    aiTutorAvailable: string;
    noMatchedTutor: string;
    noTutor: string;
  },
): CourseWorkspaceGroup {
  const publishedLectures = publishedCourseLectures(lectures, publishedLectureIds);
  const tutorAvailable = publishedLectures.length > 0 && isWorkspaceCourse(course, workspaceCourse);
  return {
    course,
    status: tutorAvailable ? "matched" : "unmatched",
    statusLabel: tutorAvailable ? labels.aiTutorAvailable : labels.noTutor,
    emptyText: labels.noMatchedTutor,
    tutorAvailable,
    courseLectures: tutorAvailable ? publishedLectures : [],
  };
}

function buildDiscoverableCourseGroup(
  workspaceCourse: UniversityCourse,
  lectures: Lecture[],
  publishedLectureIds: string[],
  labels: {
    aiTutorAvailable: string;
    noTutor: string;
    publishToEnable: string;
  },
): CourseWorkspaceGroup {
  const publishedLectures = publishedCourseLectures(lectures, publishedLectureIds);
  const tutorAvailable = publishedLectures.length > 0;
  return {
    course: workspaceCourse,
    status: tutorAvailable ? "matched" : "unmatched",
    statusLabel: tutorAvailable ? labels.aiTutorAvailable : labels.noTutor,
    emptyText: labels.publishToEnable,
    tutorAvailable,
    courseLectures: publishedLectures,
  };
}

function publishedCourseLectures(lectures: Lecture[], publishedLectureIds: string[]) {
  const published = new Set(publishedLectureIds);
  return lectures.filter((lecture) => published.has(lecture.id));
}

function isWorkspaceCourse(course: UniversityCourse, workspaceCourse: UniversityCourse) {
  return (
    course.id === workspaceCourse.id ||
    normalizeCourseTitle(course.title) === normalizeCourseTitle(workspaceCourse.title)
  );
}

function hasDemoWorkspaceAccess(workspaceCourse: UniversityCourse) {
  return readDemoWorkspaceCourse()?.id === workspaceCourse.id;
}

function hasWorkspaceAccess(workspaceCourse: UniversityCourse) {
  return hasDemoWorkspaceAccess(workspaceCourse) || hasDevelopmentWorkspaceAccess(workspaceCourse);
}

function attendanceLabel(
  status: Attendance,
  t: (key: "attendance.present" | "attendance.absent" | "attendance.unknown") => string,
) {
  if (status === "present") return t("attendance.present");
  if (status === "absent") return t("attendance.absent");
  return t("attendance.unknown");
}

function normalizeCourseTitle(title: string) {
  return title.toLowerCase().replace(/\s+/g, " ").trim();
}
