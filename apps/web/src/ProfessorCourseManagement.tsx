import { useEffect, useEffectEvent, useState } from "react";

import { deleteLectureAccess, updateCourseAccess, updateLectureAccess } from "./courseAccessApi";
import type { CourseAccessSaveInput } from "./courseAccessTypes";
import { useI18n } from "./i18n";
import {
  ProfessorCourseAccessDialog,
  type ProfessorAccessTarget,
} from "./ProfessorCourseAccessDialog";
import { ProfessorCourseManager } from "./ProfessorCourseManager";
import { ProfessorCourseUpdate } from "./ProfessorCourseUpdate";
import { deleteCourseWorkspace, listCourseWorkspaces } from "./professorApi";
import { useProfessorWorkflowRun } from "./professorWorkflowRun";
import type { CourseWorkspaceResult, LoginSession, ManagedCourseWorkspaceResult } from "./types";

export function ProfessorCourseManagement({
  onCreateCourse,
  onPreviewLecture = () => undefined,
  session,
  onWorkspaceDeleted,
}: {
  onCreateCourse: () => void;
  onPreviewLecture?: (courseId: string, lecture: CourseWorkspaceResult["lectures"][number]) => void;
  session: LoginSession;
  onWorkspaceDeleted: (courseId: string) => void;
}) {
  const { t } = useI18n();
  const [workspaces, setWorkspaces] = useState<ManagedCourseWorkspaceResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [deletingCourseId, setDeletingCourseId] = useState<string | null>(null);
  const [updatingWorkspace, setUpdatingWorkspace] = useState<CourseWorkspaceResult | null>(null);
  const [accessTarget, setAccessTarget] = useState<ProfessorAccessTarget | null>(null);
  const [accessSaving, setAccessSaving] = useState(false);
  const [accessError, setAccessError] = useState<string | null>(null);
  const [accessNotice, setAccessNotice] = useState<string | null>(null);
  const { error, notice, run, setError } = useProfessorWorkflowRun();
  const refreshCoursesFromSession = useEffectEvent(refreshCourses);

  useEffect(() => {
    void refreshCoursesFromSession();
  }, [session]);

  if (updatingWorkspace) {
    return (
      <ProfessorCourseUpdate
        session={session}
        workspace={updatingWorkspace}
        onBack={() => {
          setUpdatingWorkspace(null);
          void refreshCourses();
        }}
        onWorkspaceUpdated={(updated) => {
          setUpdatingWorkspace(updated);
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
        onManageCourseAccess={(workspace, triggerId) => {
          setAccessError(null);
          setAccessNotice(null);
          setAccessTarget({ kind: "course", triggerId, workspace });
        }}
        onManageLectureAccess={(workspace, lecture, triggerId) => {
          setAccessError(null);
          setAccessNotice(null);
          setAccessTarget({ kind: "lecture", lecture, triggerId, workspace });
        }}
        onRefresh={() => {
          void refreshCourses();
        }}
        onPreviewLecture={onPreviewLecture}
        onUpdateCourse={(courseId) => {
          setUpdatingWorkspace(workspaces.find((item) => item.course.id === courseId) ?? null);
        }}
        workspaces={workspaces}
      />
      {accessTarget ? (
        <ProfessorCourseAccessDialog
          error={accessError}
          saving={accessSaving}
          target={accessTarget}
          onClose={() => {
            setAccessError(null);
            setAccessTarget(null);
          }}
          onSave={(input) => {
            void handleAccessSave(input);
          }}
        />
      ) : null}
      {accessNotice ? (
        <p className="form-success" role="status">
          {accessNotice}
        </p>
      ) : null}
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

  async function handleAccessSave(input: CourseAccessSaveInput) {
    if (!accessTarget) return;
    const target = accessTarget;
    setAccessSaving(true);
    setAccessError(null);
    setAccessNotice(null);
    try {
      if (target.kind === "course") {
        await updateCourseAccess({
          confirmUniversityMembers: input.confirmUniversityMembers,
          courseId: target.workspace.course.id,
          rule: input.rule,
          session,
        });
      } else if (input.inheritCourseDefault) {
        await deleteLectureAccess({
          courseId: target.workspace.course.id,
          lectureId: target.lecture.id,
          session,
        });
      } else {
        await updateLectureAccess({
          confirmUniversityMembers: input.confirmUniversityMembers,
          courseId: target.workspace.course.id,
          lectureId: target.lecture.id,
          rule: input.rule,
          session,
        });
      }
      setWorkspaces(await listCourseWorkspaces(session));
      setAccessNotice(
        target.kind === "course"
          ? t("courseAccess.savedCourse", { course: target.workspace.course.title })
          : t("courseAccess.savedLecture", { lecture: target.lecture.title }),
      );
      setAccessTarget(null);
      window.setTimeout(() => document.getElementById(target.triggerId)?.focus(), 0);
    } catch (saveError) {
      setAccessError(saveError instanceof Error ? saveError.message : t("courseAccess.saveFailed"));
    } finally {
      setAccessSaving(false);
    }
  }
}
