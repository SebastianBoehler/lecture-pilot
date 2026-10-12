import {
  availableCourseLectures,
  buildCourseGroups,
  publishedCourseLectures,
} from "./dashboardCourses";
import { useState } from "react";
import { DashboardCourseWorkspaces } from "./DashboardCourseWorkspaces";
import { useI18n } from "../i18n/i18n";
import type { Attendance, Lecture, LoginSession, UniversityCourse } from "../shared/types";
import { LearnerOnboarding } from "./LearnerOnboarding";
import { NextUpCard } from "./NextUpCard";
import type { GateReviewOpening, GateReviewQueueItem } from "./reviewQueueTypes";
import { CourseSyncEmpty, CourseSyncSkeleton } from "../professor/CourseSyncState";
import type { LearnerProfileState } from "../profile/useLearnerProfile";
import { useReviewQueue } from "./useReviewQueue";
import { useDashboardWorkspaces } from "./useDashboardWorkspaces";
import { saveLectureAttendance } from "../lesson/learnerWorkspaceApi";
import { useCourseVisit } from "./useCourseVisit";

export function Dashboard({
  lectures,
  publishedLectureIds,
  session,
  workspaceCourse,
  workspaceLoadError = null,
  learnerProfileState,
  onOpen,
  onSetAttendance,
}: {
  lectures: Lecture[];
  publishedLectureIds: string[];
  session: LoginSession | null;
  workspaceCourse: UniversityCourse;
  workspaceLoadError?: string | null;
  learnerProfileState?: LearnerProfileState;
  onOpen: (
    courseId: string,
    lecture: Lecture,
    review?: GateReviewOpening,
    focusSectionId?: string,
  ) => void;
  onSetAttendance: (lectureId: string, attendance: Attendance) => void;
}) {
  const { t } = useI18n();
  const studentName = session?.display_name?.trim();
  const syncStatus = session?.university_course_sync_status ?? "ready";
  const [selectedCourseId, setSelectedCourseId] = useState(workspaceCourse.id);
  const additional = useDashboardWorkspaces(session, workspaceCourse.id);
  const courseGroups = buildCourseGroups(
    session,
    workspaceCourse,
    lectures,
    publishedLectureIds,
    {
      aiTutorAvailable: t("dashboard.aiTutorAvailable"),
      noTutor: t("dashboard.noTutor"),
    },
    additional.workspaces,
  );
  const visibleCourseGroups = syncStatus === "loading" ? [] : courseGroups;
  const singleCourse = visibleCourseGroups.filter((group) => group.tutorAvailable).length === 1;
  const activeGroup =
    visibleCourseGroups.find(
      (group) => group.tutorAvailable && group.course.id === selectedCourseId,
    ) ?? visibleCourseGroups.find((group) => group.tutorAvailable);
  const activeCourse = activeGroup?.course ?? workspaceCourse;
  const workspaceLectures = activeGroup
    ? availableCourseLectures(activeGroup.courseLectures)
    : availableCourseLectures(publishedCourseLectures(lectures, publishedLectureIds));
  const courseProfile = learnerProfileState?.profile?.courses?.find(
    (course) => course.course_id === activeCourse.id,
  );
  const reviewQueue = useReviewQueue(activeCourse.id, session);
  const visit = useCourseVisit(activeCourse.id, session);

  function openLecture(...args: Parameters<typeof onOpen>) {
    visit.markOpened(args[0], args[1].id);
    onOpen(...args);
  }

  async function openGateReview(item: GateReviewQueueItem) {
    const opening = await reviewQueue.open(item);
    const lecture = workspaceLectures.find((candidate) => candidate.id === item.lecture_id);
    if (opening && lecture) openLecture(activeCourse.id, lecture, opening);
  }

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

      {workspaceLoadError ? (
        <p className="form-error" role="alert">
          {t("dashboard.workspaceLoadError", { message: workspaceLoadError })}
        </p>
      ) : null}

      <NextUpCard
        course={activeCourse}
        lectures={workspaceLectures}
        passedLectureIds={courseProfile?.passed_lecture_ids ?? []}
        reviewQueue={reviewQueue.queue}
        onOpen={(lecture) => openLecture(activeCourse.id, lecture)}
        onOpenGateReview={(item) => void openGateReview(item)}
      />

      {reviewQueue.error ? (
        <p className="form-error" role="alert">
          {reviewQueue.error}
        </p>
      ) : null}
      {additional.error ? (
        <p className="form-error" role="alert">
          {additional.error}
        </p>
      ) : null}

      <section className="course-panel" aria-labelledby="course-workspaces">
        <div className="panel-heading course-panel-heading">
          <div>
            <h2 id="course-workspaces">
              {t(singleCourse ? "dashboard.singleCourse" : "dashboard.courseWorkspaces")}
            </h2>
            <p>
              {t(singleCourse ? "dashboard.singleCourseHelp" : "dashboard.courseWorkspacesHelp")}
            </p>
          </div>
        </div>
        <div className="course-workspace-list">
          {syncStatus === "loading" ? <CourseSyncSkeleton /> : null}
          {syncStatus !== "loading" && courseGroups.length === 0 ? (
            <CourseSyncEmpty failed={syncStatus === "error"} />
          ) : null}
          {visibleCourseGroups.length ? (
            <DashboardCourseWorkspaces
              courseGroups={visibleCourseGroups}
              newLectureIds={visit.newLectureIds}
              profileCourses={learnerProfileState?.profile?.courses}
              selectedCourseId={activeCourse.id}
              session={session}
              onSelectCourse={setSelectedCourseId}
              onOpen={(courseId, lecture) => openLecture(courseId, lecture)}
              onOpenSection={(courseId, lecture, sectionId) =>
                openLecture(courseId, lecture, undefined, sectionId)
              }
              onProgress={reviewQueue.refresh}
              onSetAttendance={(courseId, lectureId, attendance) => {
                if (courseId === workspaceCourse.id) onSetAttendance(lectureId, attendance);
                else additional.setAttendance(courseId, lectureId, attendance);
                // Persist across reloads; a failed save is retried by the next tutor turn.
                if (session) {
                  void saveLectureAttendance(courseId, lectureId, attendance, session).catch(
                    () => undefined,
                  );
                }
              }}
            />
          ) : null}
        </div>
      </section>
      {learnerProfileState?.profile && !learnerProfileState.profile.onboarding_completed ? (
        <LearnerOnboarding onComplete={learnerProfileState.saveCalibration} />
      ) : null}
    </main>
  );
}
