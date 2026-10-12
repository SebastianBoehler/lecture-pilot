import { useI18n } from "../i18n/i18n";
import type { LearningDesignApprovalInput } from "./learningDesignTypes";
import type { CourseSetup, CourseWorkspaceState } from "./professorBuilderState";
import type { publishLectureRows } from "./professorPublishRows";
import { activationLectures, courseFromSetup } from "./professorWorkspaceActivation";
import type { useProfessorWorkflowRun } from "./professorWorkflowRun";
import { requireWorkspace, type lectureFromWorkspace } from "./professorWorkspaceView";
import type {
  CanvasPublicationResult,
  LectureScheduleItem,
  LoginSession,
  UniversityCourse,
} from "../shared/types";

type WorkspaceLecture = ReturnType<typeof lectureFromWorkspace>;

/** Approve & publish reviewed drafts; one failed lecture never blocks the others. */
export function useBuilderPublish(deps: {
  session: LoginSession;
  setup: CourseSetup;
  workspace: CourseWorkspaceState | null;
  workspaceCourse: UniversityCourse | null;
  workspaceLectures: WorkspaceLecture[];
  lectureSchedule: LectureScheduleItem[];
  workflow: ReturnType<typeof useProfessorWorkflowRun>;
  canPublish: boolean;
  lectures: ReturnType<typeof publishLectureRows>;
  publishedCount: number;
  ready: boolean;
  totalCount: number;
  onPublishWorkspace: (
    courseId: string,
    lectureId: string,
    approval: LearningDesignApprovalInput,
  ) => Promise<CanvasPublicationResult>;
  onWorkspacePublished: (course: UniversityCourse, lectures: WorkspaceLecture[]) => void;
  onLecturePublished: (courseId: string, lectureId: string) => void;
}) {
  const { locale, t } = useI18n();
  const { run, setError } = deps.workflow;
  return {
    canPublish: deps.canPublish,
    isFullCourse: deps.setup.target === "full-course",
    isPublishing: deps.workflow.pendingAction === "publish",
    onPublish: (items: readonly { lectureId: string; approval: LearningDesignApprovalInput }[]) =>
      run("publish", async () => {
        const activeWorkspace = requireWorkspace(deps.workspace);
        const published = [];
        const failed: string[] = [];
        for (const { lectureId, approval } of items) {
          try {
            published.push(
              await deps.onPublishWorkspace(activeWorkspace.courseId, lectureId, approval),
            );
            deps.onLecturePublished(activeWorkspace.courseId, lectureId);
          } catch (publishError) {
            failed.push(
              publishError instanceof Error ? publishError.message : "Publishing failed.",
            );
          }
        }
        const failure = [...new Set(failed)].join("\n");
        if (!published.length) throw new Error(failure || "Publishing failed.");
        deps.onWorkspacePublished(
          deps.workspaceCourse ??
            courseFromSetup(activeWorkspace.courseId, deps.setup, deps.session),
          deps.workspaceLectures.length
            ? deps.workspaceLectures
            : activationLectures(activeWorkspace, deps.setup, deps.lectureSchedule),
        );
        if (failure) setError(failure);
        const last = published[published.length - 1];
        const when = last?.published_at ? new Date(last.published_at).toLocaleString(locale) : null;
        const version = last.version ?? 1;
        if (published.length === 1)
          return when
            ? t("builder.status.publishedOneAt", { version, when })
            : t("builder.status.publishedOne", { version });
        return when
          ? t("builder.status.publishedManyAt", { count: published.length, when })
          : t("builder.status.publishedMany", { count: published.length });
      }),
    publishedCount: deps.publishedCount,
    lectures: deps.lectures,
    ready: deps.ready,
    totalCount: deps.totalCount,
  };
}
