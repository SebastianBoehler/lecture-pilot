import { useEffect, useState } from "react";

import { useI18n } from "./i18n";
import { ProfessorCourseManager } from "./ProfessorCourseManager";
import { ProfessorCourseUpdate } from "./ProfessorCourseUpdate";
import { deleteCourseWorkspace, listCourseWorkspaces } from "./professorApi";
import { useProfessorWorkflowRun } from "./professorWorkflowRun";
import type { CourseWorkspaceResult, LoginSession } from "./types";

export function ProfessorCourseManagement({
  onCreateCourse,
  session,
  onWorkspaceDeleted,
}: {
  onCreateCourse: () => void;
  session: LoginSession;
  onWorkspaceDeleted: (courseId: string) => void;
}) {
  const { t } = useI18n();
  const [workspaces, setWorkspaces] = useState<CourseWorkspaceResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [deletingCourseId, setDeletingCourseId] = useState<string | null>(null);
  const [updatingWorkspace, setUpdatingWorkspace] = useState<CourseWorkspaceResult | null>(null);
  const { error, notice, run, setError } = useProfessorWorkflowRun();

  useEffect(() => {
    void refreshCourses();
  }, [session]);

  if (updatingWorkspace) {
    return (
      <ProfessorCourseUpdate
        session={session}
        workspace={updatingWorkspace}
        onBack={() => setUpdatingWorkspace(null)}
        onWorkspaceUpdated={(updated) => {
          setUpdatingWorkspace(updated);
          setWorkspaces((current) =>
            current.map((item) => (item.course.id === updated.course.id ? updated : item)),
          );
        }}
      />
    );
  }

  return (
    <main className="professor-screen">
      <section className="professor-page-header">
        <div>
          <h1>{t("professor.manage.title")}</h1>
          <p>{t("professor.manage.subtitle")}</p>
        </div>
      </section>
      <ProfessorCourseManager
        deletingCourseId={deletingCourseId}
        isLoading={isLoading}
        onCreateCourse={onCreateCourse}
        onDeleteCourse={(courseId) => {
          void handleDeleteCourse(courseId);
        }}
        onRefresh={() => {
          void refreshCourses();
        }}
        onUpdateCourse={(courseId) => {
          setUpdatingWorkspace(workspaces.find((item) => item.course.id === courseId) ?? null);
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
      setError(
        refreshError instanceof Error ? refreshError.message : t("professor.loadCoursesFailed"),
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function handleDeleteCourse(courseId: string) {
    if (!window.confirm(t("professor.deleteConfirm", { courseId }))) return;
    setDeletingCourseId(courseId);
    await run("delete-course", async () => {
      await deleteCourseWorkspace(courseId, session);
      setWorkspaces((current) => current.filter((item) => item.course.id !== courseId));
      onWorkspaceDeleted(courseId);
      return t("professor.deletedNotice", { courseId });
    });
    setDeletingCourseId(null);
  }
}
