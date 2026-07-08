import { useEffect, useState } from "react";

import { ProfessorCourseManager } from "./ProfessorCourseManager";
import { deleteCourseWorkspace, listCourseWorkspaces } from "./professorApi";
import { useProfessorWorkflowRun } from "./professorWorkflowRun";
import type { CourseWorkspaceResult, LoginSession } from "./types";

export function ProfessorCourseManagement({
  session,
  onWorkspaceDeleted,
}: {
  session: LoginSession;
  onWorkspaceDeleted: (courseId: string) => void;
}) {
  const [workspaces, setWorkspaces] = useState<CourseWorkspaceResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [deletingCourseId, setDeletingCourseId] = useState<string | null>(null);
  const { error, notice, run, setError } = useProfessorWorkflowRun();

  useEffect(() => {
    void refreshCourses();
  }, [session]);

  return (
    <main className="professor-screen">
      <section className="professor-page-header">
        <div>
          <h1>Manage courses</h1>
          <p>Review created course workspaces and take down broken or outdated demo courses.</p>
        </div>
      </section>
      <ProfessorCourseManager
        deletingCourseId={deletingCourseId}
        isLoading={isLoading}
        onDeleteCourse={(courseId) => {
          void handleDeleteCourse(courseId);
        }}
        onRefresh={() => {
          void refreshCourses();
        }}
        workspaces={workspaces}
      />
      {notice ? <p className="form-success">{notice}</p> : null}
      {error ? <p className="form-error">{error}</p> : null}
    </main>
  );

  async function refreshCourses() {
    setIsLoading(true);
    try {
      setWorkspaces(await listCourseWorkspaces(session));
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Could not load created courses.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleDeleteCourse(courseId: string) {
    if (!window.confirm(`Delete course workspace ${courseId} and take it down for students?`)) return;
    setDeletingCourseId(courseId);
    await run("delete-course", async () => {
      await deleteCourseWorkspace(courseId, session);
      setWorkspaces((current) => current.filter((item) => item.course.id !== courseId));
      onWorkspaceDeleted(courseId);
      return `Course workspace ${courseId} deleted.`;
    });
    setDeletingCourseId(null);
  }
}
