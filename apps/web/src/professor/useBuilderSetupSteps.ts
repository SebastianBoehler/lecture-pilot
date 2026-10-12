import { useState } from "react";

import { useI18n } from "../i18n/i18n";
import { createCourseWorkspace, getSourceBundle, proposeLectureSchedule } from "./professorApi";
import {
  isCourseSetupReady,
  type CourseSetup,
  type CourseWorkspaceState,
} from "./professorBuilderState";
import { uploadProfessorMaterials } from "./professorMaterialUpload";
import { ignoredUploadNotice } from "./professorUpload";
import type { useProfessorWorkflowRun } from "./professorWorkflowRun";
import { requireWorkspace } from "./professorWorkspaceView";
import { scheduleItemFromLecture } from "./professorWorkspaceActivation";
import type {
  CourseMaterialUploadType,
  CourseSourceRoutingManifest,
  CourseWorkspaceResult,
  LectureScheduleItem,
  LoginSession,
  SourceBundleManifest,
  SourceRouteRole,
} from "../shared/types";
import { useCourseTitleSuggestions } from "./useCourseTitleSuggestions";
import type { useProfessorSourceRouting } from "./useProfessorSourceRouting";

/** Course definition, material upload, lecture schedule and source routing actions. */
export function useBuilderSetupSteps(deps: {
  session: LoginSession;
  setup: CourseSetup;
  workspace: CourseWorkspaceState | null;
  courseReady: boolean;
  defining: boolean;
  isRestoring: boolean;
  bundle: SourceBundleManifest | null;
  supportedUploads: CourseMaterialUploadType[];
  lectureSchedule: LectureScheduleItem[];
  workspaceLectures: Parameters<typeof scheduleItemFromLecture>[0][];
  workflow: ReturnType<typeof useProfessorWorkflowRun>;
  sourceRouting: ReturnType<typeof useProfessorSourceRouting>;
  onSetupChange: (setup: CourseSetup) => void;
  onWorkspaceCreated: (created: CourseWorkspaceResult) => void;
  onBundle: (bundle: SourceBundleManifest) => void;
  onScheduleChange: (schedule: LectureScheduleItem[]) => void;
  onScheduleApplied: (applied: boolean) => void;
  onSupportedUploads: (uploads: CourseMaterialUploadType[]) => void;
  onSourcesChanged: () => void;
  onRoutingChanged: () => void;
  onRoutingConfirmed: () => void;
  /** Continues past routing when the backend accepted the proposal; false means review it. */
  continueAfterProposal: (proposed: CourseSourceRoutingManifest) => boolean;
  onCourseReady: () => void;
  navigateToSources: () => void;
}) {
  const { t } = useI18n();
  const { setup, session, workspace, sourceRouting } = deps;
  const { pendingAction, run } = deps.workflow;
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const fullCourse = setup.target === "full-course";
  const { courseSearchFailed, courseSuggestions } = useCourseTitleSuggestions({
    enabled: deps.defining && !deps.courseReady,
    personalCourses: session.university_courses ?? [],
    query: setup.courseTitle,
    session,
  });

  const defineStep = {
    courseSearchFailed,
    courseSuggestions,
    courseSourceStatuses: session.university_course_source_statuses,
    courseReady: deps.courseReady,
    isCreating: pendingAction === "create",
    isReady: isCourseSetupReady(setup),
    onCreate: () =>
      run("create", async () => {
        const created = await createCourseWorkspace(
          setup,
          session,
          fullCourse ? deps.lectureSchedule : [],
        );
        deps.onWorkspaceCreated(created);
        const sourceBundle = await getSourceBundle(created.course.id, session);
        deps.onSupportedUploads(sourceBundle.supported_uploads ?? []);
        deps.onScheduleApplied(!fullCourse);
        deps.onCourseReady();
        return fullCourse
          ? t("builder.status.createdCourse", { course: created.course.id })
          : t("builder.status.createdLecture", {
              course: created.course.id,
              lecture: created.active_lecture_id,
            });
      }),
    onSetupChange: deps.onSetupChange,
    session,
    setup,
  };

  const uploadStep = {
    bundle: deps.bundle,
    courseReady: deps.courseReady,
    lectureSchedule: deps.lectureSchedule,
    pendingAction,
    setup,
    uploadFiles,
    supportedUploads: deps.supportedUploads,
    workspaceReady: Boolean(workspace),
    onUploadFilesChange: setUploadFiles,
    onScheduleChange: deps.onScheduleChange,
    onUpload: () =>
      run("upload", async () => {
        const activeWorkspace = requireWorkspace(workspace);
        const result = await uploadProfessorMaterials({
          courseId: activeWorkspace.courseId,
          files: uploadFiles,
          session,
          supportedUploads: deps.supportedUploads,
        });
        if (result.bundle) deps.onBundle(result.bundle);
        if (result.uploaded.length > 0 || result.mutationUncertain) {
          deps.onSourcesChanged();
          if (fullCourse) deps.onScheduleApplied(false);
        }
        if (result.error) throw result.error;
        if (fullCourse) {
          const proposal = await proposeLectureSchedule({
            courseId: activeWorkspace.courseId,
            count: Number(setup.lectureCount) || null,
            firstLectureDate: setup.firstLectureDate,
            session,
          });
          deps.onScheduleChange(proposal.lectures);
        }
        const autoConfirmed =
          !fullCourse &&
          deps.continueAfterProposal(await sourceRouting.propose(activeWorkspace.courseId));
        setUploadFiles([]);
        if (autoConfirmed) return t("builder.status.routingAutoConfirmed");
        const ignoredText = ignoredUploadNotice(result.ignored, t);
        if (result.uploaded.length === 1) {
          const [uploaded] = result.uploaded;
          return `${t("builder.status.uploadedOne", { path: uploaded.path, kind: uploaded.kind })}${ignoredText}`;
        }
        return `${t("builder.status.uploadedMany", { count: result.uploaded.length })}${ignoredText}`;
      }),
    onApplySchedule: () =>
      run("apply-schedule", async () => {
        const activeWorkspace = requireWorkspace(workspace);
        const created = await createCourseWorkspace(
          setup,
          session,
          deps.lectureSchedule,
          activeWorkspace.courseId,
        );
        deps.onWorkspaceCreated(created);
        deps.onScheduleApplied(true);
        deps.navigateToSources();
        if (deps.continueAfterProposal(await sourceRouting.propose(created.course.id)))
          return t("builder.status.routingAutoConfirmed");
        return t("builder.status.scheduleApplied", { count: created.lectures.length });
      }),
  };

  const routingStep = {
    isLoading: deps.isRestoring,
    isProposing:
      pendingAction === "apply-schedule" ||
      pendingAction === "upload" ||
      pendingAction === "regenerate-routing",
    isSaving: pendingAction === "confirm-routing" || pendingAction === "regenerate-routing",
    lectures: deps.lectureSchedule.length
      ? deps.lectureSchedule
      : deps.workspaceLectures.map(scheduleItemFromLecture),
    routing: sourceRouting.routing,
    onRouteChange: (path: string, role: SourceRouteRole, lectureId: string | null) => {
      sourceRouting.updateRoute(path, role, lectureId);
      deps.onRoutingChanged();
    },
    onRegenerate: () =>
      run("regenerate-routing", async () => {
        await sourceRouting.regenerate(requireWorkspace(workspace).courseId);
        deps.onRoutingChanged();
        return t("builder.status.routingRebuilt");
      }),
    onConfirm: () =>
      run("confirm-routing", async () => {
        await sourceRouting.confirm(requireWorkspace(workspace).courseId);
        deps.onRoutingConfirmed();
        return t("builder.status.routingConfirmed");
      }),
  };

  return { defineStep, uploadStep, routingStep };
}
