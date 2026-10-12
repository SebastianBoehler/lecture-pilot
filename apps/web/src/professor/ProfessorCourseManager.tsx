import { ProfessorLegacyCourseRow } from "./ProfessorLegacyCourseRow";
import { courseSetupState, ProfessorCourseStatus } from "./ProfessorCourseStatus";
import { ProfessorLanguageVariants } from "./ProfessorLanguageVariants";
import { useI18n } from "../i18n/i18n";
import {
  accessAudienceLabel,
  defaultReleaseLabel,
  ProfessorLectureAccessStatus,
} from "./ProfessorLectureAccessStatus";
import { ExamReadinessPanel } from "../exam/ExamReadinessPanel";
import type { Lecture, LoginSession, ManagedCourseWorkspaceResult } from "../shared/types";

type ProfessorCourseManagerProps = {
  deletingCourseId: string | null;
  isLoading: boolean;
  onCreateCourse: () => void;
  onDeleteCourse: (courseId: string) => void;
  onManageCourseAccess: (workspace: ManagedCourseWorkspaceResult, triggerId: string) => void;
  onManageLectureAccess: (
    workspace: ManagedCourseWorkspaceResult,
    lecture: Lecture,
    triggerId: string,
  ) => void;
  onRefresh: () => void;
  onPreviewLecture: (courseId: string, lecture: Lecture) => void;
  onResumeCourse: (workspace: ManagedCourseWorkspaceResult) => void;
  onShareCourse: (workspace: ManagedCourseWorkspaceResult) => void;
  onUpdateCourse: (courseId: string) => void;
  session: LoginSession;
  workspaces: ManagedCourseWorkspaceResult[];
};

export function ProfessorCourseManager({
  deletingCourseId,
  isLoading,
  onCreateCourse,
  onDeleteCourse,
  onManageCourseAccess,
  onManageLectureAccess,
  onRefresh,
  onPreviewLecture,
  onResumeCourse,
  onShareCourse,
  onUpdateCourse,
  session,
  workspaces,
}: ProfessorCourseManagerProps) {
  const { t } = useI18n();
  return (
    <section className="course-manager-panel" aria-labelledby="created-courses-heading">
      <div className="course-manager-header" data-tour="course-management-workflow">
        <div>
          <h2 id="created-courses-heading">{t("professor.createdCourses")}</h2>
        </div>
        <button className="refresh-button" disabled={isLoading} type="button" onClick={onRefresh}>
          {isLoading ? t("professor.refreshing") : t("professor.refresh")}
        </button>
        <button className="refresh-button primary-action" type="button" onClick={onCreateCourse}>
          {t("professor.createCourse")}
        </button>
      </div>
      {workspaces.length ? (
        <div className="created-course-list">
          {workspaces.map((workspace) =>
            workspace.legacyLectureIds?.length ? (
              <ProfessorLegacyCourseRow
                key={workspace.course.id}
                workspace={workspace}
                deleting={deletingCourseId === workspace.course.id}
                onDelete={onDeleteCourse}
              />
            ) : (
              <article className="created-course-row" key={workspace.course.id}>
                <div className="created-course-summary">
                  <div className="created-course-title">
                    <strong>{workspace.course.title}</strong>
                    <span>{workspace.course.term}</span>
                  </div>
                  <div className="created-course-meta">
                    <strong>
                      {t("professor.configuredLectures", { count: workspace.lectures.length })}
                    </strong>
                    <span>
                      {t("courseAccess.default", {
                        audience: accessAudienceLabel(
                          workspace.accessSummary.default_rule.audience,
                          t,
                        ),
                        release: defaultReleaseLabel(workspace.accessSummary.default_rule, t),
                      })}
                    </span>
                  </div>
                  <div className="created-course-actions">
                    <button
                      aria-label={t("courseAccess.manageDefaultAria", {
                        course: workspace.course.title,
                      })}
                      className="refresh-button"
                      id={`course-access-${workspace.course.id}`}
                      type="button"
                      onClick={(event) => onManageCourseAccess(workspace, event.currentTarget.id)}
                    >
                      {t("courseAccess.manageDefault")}
                    </button>
                    {courseSetupState(workspace).kind !== "published" ? (
                      <button
                        className="refresh-button primary-action"
                        type="button"
                        aria-label={t("professor.setup.resumeAria", {
                          course: workspace.course.title,
                        })}
                        onClick={() => onResumeCourse(workspace)}
                      >
                        {t("professor.setup.resume")}
                      </button>
                    ) : null}
                    <button
                      className="refresh-button"
                      type="button"
                      aria-label={t("share.actionAria", { course: workspace.course.title })}
                      onClick={() => onShareCourse(workspace)}
                    >
                      {t("share.action")}
                    </button>
                    {courseSetupState(workspace).published > 0 ? (
                      <button
                        className="refresh-button"
                        type="button"
                        onClick={() => onUpdateCourse(workspace.course.id)}
                      >
                        {t("professor.update")}
                      </button>
                    ) : null}
                    {workspace.publishedLectureIds?.length ? (
                      <ExamReadinessPanel
                        compact
                        course={workspace.course}
                        lectures={workspace.lectures.filter((lecture) =>
                          workspace.publishedLectureIds?.includes(lecture.id),
                        )}
                        mode="professor-preview"
                        session={session}
                        onOpenLecture={(lecture) => onPreviewLecture(workspace.course.id, lecture)}
                      />
                    ) : null}
                    <button
                      className="refresh-button delete-course-button"
                      disabled={deletingCourseId === workspace.course.id}
                      type="button"
                      aria-label={t("professor.deleteCourse", { course: workspace.course.title })}
                      onClick={() => onDeleteCourse(workspace.course.id)}
                    >
                      {deletingCourseId === workspace.course.id
                        ? t("professor.deleting")
                        : t("professor.delete")}
                    </button>
                  </div>
                </div>
                <ProfessorCourseStatus workspace={workspace} />
                <details className="created-course-lectures" open={workspaces.length === 1}>
                  <summary>{t("professor.preview.lectures")}</summary>
                  <ul>
                    {workspace.lectures.map((lecture) => {
                      const accessSummary = workspace.accessSummary.lectures.find(
                        (summary) => summary.lecture_id === lecture.id,
                      );
                      if (!accessSummary) {
                        throw new Error(`Missing access summary for ${lecture.id}.`);
                      }
                      return (
                        <li key={lecture.id}>
                          <span className="created-lecture-number">{lecture.number}</span>
                          <span className="created-lecture-copy">
                            <span className="created-lecture-title">{lecture.title}</span>
                          </span>
                          <ProfessorLectureAccessStatus summary={accessSummary} />
                          <span className="created-lecture-actions">
                            {accessSummary.content_ready ? (
                              <button
                                className="refresh-button"
                                type="button"
                                onClick={() => onPreviewLecture(workspace.course.id, lecture)}
                              >
                                {t("professor.preview.open")}
                              </button>
                            ) : null}
                            <button
                              aria-label={t("courseAccess.manageAria", { lecture: lecture.title })}
                              className="refresh-button"
                              id={`lecture-access-${workspace.course.id}-${lecture.id}`}
                              type="button"
                              onClick={(event) =>
                                onManageLectureAccess(workspace, lecture, event.currentTarget.id)
                              }
                            >
                              {t("courseAccess.manage")}
                            </button>
                          </span>
                          {accessSummary.content_ready ? (
                            <ProfessorLanguageVariants
                              courseId={workspace.course.id}
                              lectureId={lecture.id}
                              session={session}
                            />
                          ) : null}
                        </li>
                      );
                    })}
                  </ul>
                </details>
              </article>
            ),
          )}
        </div>
      ) : isLoading ? (
        <p className="empty-course-manager" role="status">
          {t("professor.loadingCourses")}
        </p>
      ) : (
        <p className="empty-course-manager">{t("professor.noCreatedCourses")}</p>
      )}
    </section>
  );
}
