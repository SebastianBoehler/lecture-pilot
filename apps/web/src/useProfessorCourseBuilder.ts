import { useReducer, useState } from "react";

import { builderFlowReducer, initialBuilderFlow } from "./builderFlowMachine";
import type { LearningDesignApprovalInput } from "./learningDesignTypes";
import { builderSteps, initialBuilderStep, type BuilderStep } from "./ProfessorBuilderStepper";
import {
  clearSavedFlow,
  defaultCourseSetup,
  readSavedFlow,
  type CourseSetup,
} from "./professorBuilderState";
import { useProfessorWorkflowRun } from "./professorWorkflowRun";
import type { lectureFromWorkspace } from "./professorWorkspaceView";
import { useProfessorPracticeDesignGate } from "./practiceDesignGate";
import { hasNoAssignedEvidence } from "./sourceRoutingView";
import type {
  CanvasPublicationResult,
  CourseSourceRoutingManifest,
  CourseWorkspaceResult,
  LoginSession,
  UniversityCourse,
} from "./types";
import { useBuilderGeneration } from "./useBuilderGeneration";
import { useBuilderMedia } from "./useBuilderMedia";
import { useBuilderPublish } from "./useBuilderPublish";
import { useBuilderRestore } from "./useBuilderRestore";
import { useBuilderSetupSteps } from "./useBuilderSetupSteps";
import { useBuilderWorkspace } from "./useBuilderWorkspace";
import { useProfessorSourceRouting } from "./useProfessorSourceRouting";

type WorkspaceLecture = ReturnType<typeof lectureFromWorkspace>;

export type ProfessorCourseBuilderProps = {
  session: LoginSession;
  onPublishWorkspace: (
    courseId: string,
    lectureId: string,
    approval: LearningDesignApprovalInput,
  ) => Promise<CanvasPublicationResult>;
  onWorkspacePublished: (course: UniversityCourse, lectures: WorkspaceLecture[]) => void;
  previewWorkspaceUrl: (courseId: string, lecture: WorkspaceLecture) => string;
};

/**
 * Composes the course builder from focused hooks. Where the builder resumes and how drafts
 * retry is decided by the pure `builderFlowMachine` reducer.
 */
export function useProfessorCourseBuilder(props: ProfessorCourseBuilderProps) {
  const { session } = props;
  const [savedFlow] = useState(readSavedFlow);
  const course = useBuilderWorkspace({
    savedFlow,
    session,
    previewWorkspaceUrl: props.previewWorkspaceUrl,
  });
  const { setup, workspace, fullCourse, bundleReady, targetIds } = course;
  const [flow, dispatch] = useReducer(builderFlowReducer, savedFlow, (saved) =>
    initialBuilderFlow(
      initialBuilderStep({
        bundleReady: saved.bundleReady,
        canvasReady: saved.canvasReady,
        courseReady: saved.courseReady && Boolean(saved.workspace),
      }),
    ),
  );
  const setActiveStep = (step: BuilderStep) => dispatch({ type: "navigate", step });
  const workflow = useProfessorWorkflowRun();
  const sourceRouting = useProfessorSourceRouting(session);
  const routingReady = Boolean(
    sourceRouting.routing?.confirmed && !hasNoAssignedEvidence(sourceRouting.routing.routes),
  );
  const practiceDesign = useProfessorPracticeDesignGate({
    courseId: workspace?.courseId ?? null,
    routingReady,
    session,
    targetLectures: course.targetLectures.map((lecture) => ({
      id: lecture.id,
      label: `${lecture.number} · ${lecture.title}`,
    })),
  });
  const designReady = routingReady && practiceDesign.designReady;
  const media = useBuilderMedia({
    session,
    initialQuery: savedFlow.query,
    setup,
    workspace,
    bundle: course.bundle,
    canvas: flow.canvas,
    lectures: course.targetLectures,
    active: flow.activeStep === "media",
    workflow,
    onContinue: async () => {
      await requireConfirmedRouting(workspaceId());
      dispatch({ type: "media-continued" });
    },
    onMediaChanged: () => dispatch({ type: "media-changed" }),
  });

  function workspaceId() {
    if (!workspace) throw new Error("Create the course workspace first.");
    return workspace.courseId;
  }

  async function requireConfirmedRouting(courseId: string, navigate = true) {
    const current = await sourceRouting.load(courseId);
    if (current.confirmed && !hasNoAssignedEvidence(current.routes)) return current;
    if (navigate) setActiveStep("sources");
    throw new Error(
      "Source assignments changed. Review and confirm source assignments again before generating canvases.",
    );
  }

  function resetCanvasState() {
    dispatch({ type: "canvas-reset" });
    media.reset();
  }

  function resetGeneratedState() {
    sourceRouting.reset();
    practiceDesign.reset();
    resetCanvasState();
  }

  function routingConfirmed() {
    practiceDesign.reset();
    media.reset();
    dispatch({ type: "routing-confirmed" });
  }

  /** An automatically accepted assignment continues like a confirmed one; it stays editable. */
  function continueAfterProposal(proposed: CourseSourceRoutingManifest) {
    if (proposed.confirmed) routingConfirmed();
    else setActiveStep("sources");
    return proposed.confirmed;
  }

  function updateSetup(nextSetup: CourseSetup) {
    resetGeneratedState();
    course.clear(nextSetup);
    media.selectLecture("");
    setActiveStep("define");
  }

  function workspaceCreated(created: CourseWorkspaceResult) {
    course.created(created);
    media.selectLecture(created.active_lecture_id);
    resetGeneratedState();
  }

  const restore = useBuilderRestore({
    savedFlow,
    current: {
      setup,
      workspace,
      courseReady: course.courseReady,
      bundleReady,
      canvasReady: Boolean(flow.canvas),
      lectureSchedule: course.lectureSchedule,
      query: media.query,
    },
    session,
    setup,
    dispatch,
    loadRouting: sourceRouting.load,
    onRestored: course.restored,
    onWorkspaceMissing: () => {
      clearSavedFlow();
      media.setQuery("");
      updateSetup({
        ...setup,
        courseTitle: "",
        firstLectureDate: "",
        lectureCount: "",
        lectureNumber: "",
        lectureTitle: "",
      });
    },
    setError: workflow.setError,
  });
  const generateStep = useBuilderGeneration({
    session,
    workspace,
    flow,
    dispatch,
    workflow,
    readyLectureIds: practiceDesign.readyLectureIds,
    targetLectureIds: targetIds,
    requireReady: async (ids, navigate) => {
      await requireConfirmedRouting(workspaceId(), navigate);
      try {
        await practiceDesign.requireCurrentApprovals(ids);
      } catch (approvalError) {
        if (navigate) setActiveStep("design");
        throw approvalError;
      }
    },
    canGenerate: Boolean(
      bundleReady && routingReady && practiceDesign.readyLectureIds.length && workspace,
    ),
    allGoalsApproved: designReady,
    isFullCourse: fullCourse,
    previewLectures: course.previewLectures(flow.generatedIds, Boolean(flow.canvas)),
  });
  const setupSteps = useBuilderSetupSteps({
    session,
    setup,
    workspace,
    courseReady: course.courseReady,
    defining: flow.activeStep === "define",
    isRestoring: restore.isRestoring,
    bundle: course.bundle,
    supportedUploads: course.supportedUploads,
    lectureSchedule: course.lectureSchedule,
    workspaceLectures: course.workspaceLectures,
    workflow,
    sourceRouting,
    onSetupChange: updateSetup,
    onWorkspaceCreated: workspaceCreated,
    onSupportedUploads: course.setSupportedUploads,
    onBundle: course.bundleChanged,
    onScheduleChange: course.setLectureSchedule,
    onScheduleApplied: course.setScheduleApplied,
    onSourcesChanged: resetGeneratedState,
    onRoutingChanged: () => {
      practiceDesign.reset();
      resetCanvasState();
    },
    onRoutingConfirmed: routingConfirmed,
    continueAfterProposal,
    onCourseReady: () => {
      course.markCourseReady();
      setActiveStep("upload");
    },
    navigateToSources: () => setActiveStep("sources"),
  });
  const publishStep = useBuilderPublish({
    ...props,
    setup,
    workspace,
    workspaceCourse: course.workspaceCourse,
    workspaceLectures: course.workspaceLectures,
    lectureSchedule: course.lectureSchedule,
    workflow,
    canPublish: Boolean(flow.canvas && workspace),
    lectures: course.publishLectures,
    publishedCount: course.publishedCount,
    ready: course.published,
    totalCount: targetIds.length,
    onLecturePublished: course.lecturePublished,
  });

  return {
    activeStep: flow.activeStep,
    draftRestoreRevision: flow.draftRestoreRevision,
    ...setupSteps,
    error: workflow.error,
    generateStep,
    generationWarnings: [...flow.warnings],
    isRestoring: restore.isRestoring,
    mediaStep: {
      ...media.step,
      canContinue: Boolean(bundleReady && routingReady && workspace),
      ready: media.ready,
    },
    notice: workflow.notice,
    publishStep,
    practiceDesignStep: practiceDesign.practiceDesignStep,
    restoreWorkspace: () => void restore.restore(workspace, { quietDraftMiss: true }),
    courseTitle: setup.courseTitle,
    startNewCourse: () => {
      clearSavedFlow();
      updateSetup(defaultCourseSetup);
    },
    setActiveStep,
    steps: builderSteps({
      bundleReady,
      canvasReady: Boolean(flow.canvas),
      courseReady: course.courseReady,
      designAvailable: sourceRouting.status === "stale",
      designReady,
      draftReviewed: flow.draftReviewed,
      reviewAvailable: bundleReady && (!fullCourse || course.scheduleApplied),
      reviewReady: media.ready || flow.mediaReviewed,
      routingReady,
      workspacePublished: course.published,
    }),
    workspace,
  };
}
