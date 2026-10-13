import { useState } from "react";

import { useI18n } from "../i18n/i18n";
import type { Lecture, LoginSession, ManagedCourseWorkspaceResult } from "../shared/types";
import { CourseDraftReviewPanel } from "./CourseDraftReviewPanel";
import { CourseGoalReviewPanel } from "./CourseGoalReviewPanel";
import { CourseChangeRequestDialog } from "./CourseChangeRequestDialog";
import { canRequestChange, courseLectureSummary } from "./courseLectureStatus";
import type { LectureState } from "./courseLectureStateTypes";
import { CourseLectureRow } from "./CourseLectureRow";
import { CourseStaleGoalsPanel } from "./CourseStaleGoalsPanel";
import { CourseUpdateDialog } from "./CourseUpdateDialog";
import { ProfessorShareCourseDialog } from "./ProfessorShareCourseDialog";
import { useCourseLectureActions } from "./useCourseLectureActions";
import { useCourseLectureStates } from "./useCourseLectureStates";

/** One page per managed course: lecture states, one next step each, and course updates. */
export function ProfessorCoursePage({
  workspace,
  session,
  onBack,
  onCourseChanged,
  onPreviewLecture,
  onResumeCourse,
}: {
  workspace: ManagedCourseWorkspaceResult;
  session: LoginSession;
  onBack: () => void;
  onCourseChanged: () => void;
  onPreviewLecture: (courseId: string, lecture: Lecture) => void;
  onResumeCourse: (workspace: ManagedCourseWorkspaceResult) => void;
}) {
  const { t } = useI18n();
  const courseId = workspace.course.id;
  const { states, error, refresh } = useCourseLectureStates(courseId, session);
  const actions = useCourseLectureActions({
    courseId,
    session,
    refresh,
    onPublished: onCourseChanged,
  });
  const [openId, setOpenId] = useState<string | null>(null);
  const [dialog, setDialog] = useState<"update" | "share" | null>(null);
  const [changeId, setChangeId] = useState<string | null>(null);
  const lectures = states?.lectures ?? [];
  const summary = courseLectureSummary(lectures);
  const ready = lectures.filter((lecture) => lecture.next_action === "review_draft");
  const publishing = ready.some((lecture) => actions.pending[lecture.lecture_id]);
  const previewable = (lecture: LectureState) =>
    lecture.published
      ? workspace.lectures.find((item) => item.id === lecture.lecture_id)
      : undefined;
  const firstPublished = lectures.map(previewable).find(Boolean);
  const changeLecture = lectures.find((lecture) => lecture.lecture_id === changeId);

  return (
    <main className="professor-screen course-page">
      <button className="course-back" type="button" onClick={onBack}>
        {t("coursePage.back")}
      </button>
      <header className="course-page-header">
        <div className="course-page-heading">
          <h1>{workspace.course.title}</h1>
          <p>
            {workspace.course.term ? <span>{workspace.course.term}</span> : null}
            {states ? <span>{summaryText()}</span> : null}
          </p>
        </div>
        <div className="course-page-actions">
          <button
            className="course-row-button"
            data-primary
            type="button"
            onClick={() => setDialog("update")}
          >
            {t("coursePage.upload")}
          </button>
          <button className="course-row-button" type="button" onClick={() => setDialog("share")}>
            {t("share.action")}
          </button>
          {firstPublished ? (
            <button
              className="course-row-button"
              type="button"
              onClick={() => onPreviewLecture(courseId, firstPublished)}
            >
              {t("coursePage.preview")}
            </button>
          ) : null}
        </div>
      </header>

      {ready.length ? (
        <section className="course-publish-bar" aria-label={t("coursePage.draft.approve")}>
          <p>{t("coursePage.publishAllHelp")}</p>
          <button
            className="course-row-button"
            data-primary
            type="button"
            disabled={publishing}
            onClick={() => void actions.publishAll(ready.map((lecture) => lecture.lecture_id))}
          >
            {t("coursePage.publishAll", { count: ready.length })}
          </button>
        </section>
      ) : null}

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      {!states && !error ? <p role="status">{t("coursePage.loading")}</p> : null}
      {states ? (
        <table className="course-lecture-table">
          <caption className="visually-hidden">{t("coursePage.lectures")}</caption>
          <thead>
            <tr>
              <th scope="col">{t("coursePage.column.number")}</th>
              <th scope="col">{t("coursePage.column.lecture")}</th>
              <th scope="col">{t("coursePage.column.date")}</th>
              <th scope="col">{t("coursePage.column.status")}</th>
              <th scope="col">{t("coursePage.column.action")}</th>
            </tr>
          </thead>
          <tbody>
            {lectures.map((lecture) => {
              const id = lecture.lecture_id;
              const preview = previewable(lecture);
              return (
                <CourseLectureRow
                  key={id}
                  lecture={lecture}
                  open={openId === id}
                  pending={actions.pending[id]}
                  error={actions.errors[id]}
                  panel={panel(lecture)}
                  onToggle={() => setOpenId((current) => (current === id ? null : id))}
                  onConfirmRouting={() => onResumeCourse(workspace)}
                  onStartDraft={() => void actions.startDraft(id)}
                  onPreview={preview ? () => onPreviewLecture(courseId, preview) : undefined}
                  onRequestChange={canRequestChange(lecture) ? () => setChangeId(id) : undefined}
                />
              );
            })}
          </tbody>
        </table>
      ) : null}

      {dialog === "update" ? (
        <CourseUpdateDialog
          courseId={courseId}
          courseTitle={workspace.course.title}
          session={session}
          onClose={() => setDialog(null)}
          onApplied={() => {
            setDialog(null);
            onCourseChanged();
            void refresh();
          }}
        />
      ) : null}
      {changeLecture ? (
        <CourseChangeRequestDialog
          courseId={courseId}
          lecture={changeLecture}
          session={session}
          onClose={() => setChangeId(null)}
          onSubmitted={() => {
            setChangeId(null);
            void refresh();
          }}
        />
      ) : null}
      {dialog === "share" ? (
        <ProfessorShareCourseDialog
          session={session}
          workspace={workspace}
          onClose={() => setDialog(null)}
        />
      ) : null}
    </main>
  );

  function summaryText() {
    const parts = [
      summary.total === 1
        ? t("coursePage.summary.lecturesOne")
        : t("coursePage.summary.lectures", { count: summary.total }),
      t("coursePage.summary.published", { count: summary.published }),
    ];
    if (summary.needsReview) {
      parts.push(
        summary.needsReview === 1
          ? t("coursePage.summary.reviewOne")
          : t("coursePage.summary.review", { count: summary.needsReview }),
      );
    }
    return parts.join(", ");
  }

  function panel(lecture: LectureState) {
    const id = lecture.lecture_id;
    if (lecture.next_action === "keep_or_regenerate_goals") {
      return (
        <CourseStaleGoalsPanel
          courseId={courseId}
          lecture={lecture}
          session={session}
          pending={actions.pending[id]}
          onKeep={() => void actions.keepGoals(id)}
          onRegenerate={(previous) => void actions.regenerateGoals(id, previous)}
        />
      );
    }
    if (lecture.next_action === "review_goals") {
      return (
        <CourseGoalReviewPanel
          courseId={courseId}
          lecture={lecture}
          session={session}
          previousGoals={actions.previousGoals[id]}
          onApproved={() => void actions.goalsApproved(id)}
        />
      );
    }
    if (lecture.next_action === "review_draft") {
      return (
        <CourseDraftReviewPanel
          courseId={courseId}
          lecture={lecture}
          session={session}
          pending={actions.pending[id]}
          onPublish={() => void actions.publish(id)}
        />
      );
    }
    return null;
  }
}
