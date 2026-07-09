import { useI18n } from "./i18n";
import type { CourseWorkspaceResult } from "./types";

type ProfessorCourseManagerProps = {
  deletingCourseId: string | null;
  isLoading: boolean;
  onDeleteCourse: (courseId: string) => void;
  onRefresh: () => void;
  workspaces: CourseWorkspaceResult[];
};

export function ProfessorCourseManager({
  deletingCourseId,
  isLoading,
  onDeleteCourse,
  onRefresh,
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
      </div>
      {workspaces.length ? (
        <div className="created-course-list">
          {workspaces.map((workspace) => (
            <article className="created-course-row" key={workspace.course.id}>
              <div>
                <strong>{workspace.course.title}</strong>
                <span>{workspace.course.id}</span>
              </div>
              <p>{t("professor.publishedLectures", { count: workspace.lectures.length })}</p>
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
            </article>
          ))}
        </div>
      ) : (
        <p className="empty-course-manager">{t("professor.noCreatedCourses")}</p>
      )}
    </section>
  );
}
