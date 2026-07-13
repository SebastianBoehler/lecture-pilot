import { useI18n } from "./i18n";
import type { CourseWorkspaceResult } from "./types";

type ProfessorCourseManagerProps = {
  deletingCourseId: string | null;
  isLoading: boolean;
  onCreateCourse: () => void;
  onDeleteCourse: (courseId: string) => void;
  onRefresh: () => void;
  onPreviewLecture: (courseId: string, lecture: CourseWorkspaceResult["lectures"][number]) => void;
  onUpdateCourse: (courseId: string) => void;
  workspaces: CourseWorkspaceResult[];
};

export function ProfessorCourseManager({
  deletingCourseId,
  isLoading,
  onCreateCourse,
  onDeleteCourse,
  onRefresh,
  onPreviewLecture,
  onUpdateCourse,
  workspaces,
}: ProfessorCourseManagerProps) {
  const { t } = useI18n();
  return (
    <section className="course-manager-panel" aria-labelledby="created-courses-heading">
      <div className="course-manager-header">
        <div>
          <h2 id="created-courses-heading">{t("professor.createdCourses")}</h2>
          <p>{t("professor.createdCoursesHelp")}</p>
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
          {workspaces.map((workspace) => (
            <article className="created-course-row" key={workspace.course.id}>
              <div className="created-course-summary">
                <div className="created-course-title">
                  <strong>{workspace.course.title}</strong>
                  <span>
                    {workspace.course.professor} · {workspace.course.term}
                  </span>
                </div>
                <div className="created-course-meta">
                  <strong>{t("professor.courseWorkspace")}</strong>
                  <span>
                    {t("professor.configuredLectures", { count: workspace.lectures.length })}
                  </span>
                  <small>{workspace.course.id}</small>
                </div>
                <div className="created-course-actions">
                  <button
                    className="refresh-button"
                    type="button"
                    onClick={() => onUpdateCourse(workspace.course.id)}
                  >
                    {t("professor.update")}
                  </button>
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
              <details className="created-course-lectures" open={workspaces.length === 1}>
                <summary>{t("professor.preview.lectures")}</summary>
                <ul>
                  {workspace.lectures.map((lecture) => {
                    const isPublished = workspace.publishedLectureIds?.includes(lecture.id);
                    return (
                      <li key={lecture.id}>
                        <span className="created-lecture-number">{lecture.number}</span>
                        <span className="created-lecture-title">{lecture.title}</span>
                        {isPublished ? (
                          <button
                            className="refresh-button"
                            type="button"
                            onClick={() => onPreviewLecture(workspace.course.id, lecture)}
                          >
                            {t("professor.preview.open")}
                          </button>
                        ) : (
                          <span className="created-lecture-status">
                            {t("professor.preview.unpublished")}
                          </span>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </details>
            </article>
          ))}
        </div>
      ) : (
        <p className="empty-course-manager">{t("professor.noCreatedCourses")}</p>
      )}
    </section>
  );
}
