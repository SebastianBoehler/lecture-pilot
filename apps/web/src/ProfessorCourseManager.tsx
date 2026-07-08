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
  return (
    <section className="course-manager-panel" aria-labelledby="created-courses-heading">
      <div className="course-manager-header">
        <div>
          <h2 id="created-courses-heading">Created courses</h2>
          <p>Manage published or draft course workspaces independently from the creation flow.</p>
        </div>
        <button className="refresh-button" disabled={isLoading} type="button" onClick={onRefresh}>
          {isLoading ? "Refreshing..." : "Refresh"}
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
              <p>{workspace.lectures.length} lecture{workspace.lectures.length === 1 ? "" : "s"}</p>
              <button
                className="refresh-button delete-course-button"
                disabled={deletingCourseId === workspace.course.id}
                type="button"
                aria-label={`Delete ${workspace.course.title}`}
                onClick={() => onDeleteCourse(workspace.course.id)}
              >
                {deletingCourseId === workspace.course.id ? "Deleting..." : "Delete"}
              </button>
            </article>
          ))}
        </div>
      ) : (
        <p className="empty-course-manager">No created course workspaces yet.</p>
      )}
    </section>
  );
}
