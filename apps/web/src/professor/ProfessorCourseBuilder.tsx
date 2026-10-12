import { useEffect, useRef, useState } from "react";
import { ProfessorLanguageVariants } from "./ProfessorLanguageVariants";
import { ProfessorReviewStep } from "./ProfessorReviewStep";
import { useAutomaticCanvasGeneration } from "./useAutomaticCanvasGeneration";
import { ProfessorImplementationChanges } from "./ProfessorImplementationChanges";
import { useI18n } from "../i18n/i18n";
import { ProfessorBuilderStepper } from "./ProfessorBuilderStepper";
import { ProfessorCanvasDraftStep } from "./ProfessorCanvasDraftStep";
import { ProfessorCourseSetupStep } from "./ProfessorCourseSetupStep";
import { ProfessorGenerationWarnings } from "./ProfessorGenerationWarnings";
import { ProfessorBuilderMaterials } from "./ProfessorBuilderMaterials";
import { builderStage, type BuilderStage } from "./builderStages";
import { ProfessorPracticeDesignStep } from "./ProfessorPracticeDesignStep";
import { ProfessorPublishStep } from "./ProfessorPublishStep";
import {
  useProfessorCourseBuilder,
  type ProfessorCourseBuilderProps,
} from "./useProfessorCourseBuilder";
import { learningDesignApprovalInput } from "./learningDesignApi";
import { useProfessorLearningDesignReviews } from "./useProfessorLearningDesignReviews";
import { useVersionUpdateActivity } from "../shell/VersionUpdateBoundary";

export function ProfessorCourseBuilder(props: ProfessorCourseBuilderProps) {
  const { t } = useI18n();
  const builder = useProfessorCourseBuilder(props);
  // Each lecture drafts as soon as its goals are approved; the professor keeps reviewing others.
  // A re-approved, changed plan drafts again; an unchanged failed draft waits for Retry.
  const [draftedRevisions, setDraftedRevisions] = useState<Record<string, string>>({});
  const waitingLectureIds = builder.generateStep.readyLectureIds.filter((id) => {
    const progress = builder.generateStep.generationProgress.find((item) => item.lectureId === id);
    const revision = builder.practiceDesignStep.designs[id]?.revision;
    if (id in draftedRevisions && draftedRevisions[id] !== revision) {
      return progress?.status !== "generating";
    }
    return progress
      ? progress.status === "pending"
      : !builder.generateStep.generatedIds.includes(id);
  });
  useAutomaticCanvasGeneration({
    revision: JSON.stringify([
      builder.workspace?.courseId,
      waitingLectureIds.map((id) => [id, builder.practiceDesignStep.designs[id]?.revision]),
    ]),
    ready:
      waitingLectureIds.length > 0 &&
      builder.generateStep.canGenerate &&
      !builder.isRestoring &&
      builder.uploadStep.pendingAction === null &&
      !builder.practiceDesignStep.preparing,
    start: () => {
      setDraftedRevisions((current) => ({
        ...current,
        ...Object.fromEntries(
          waitingLectureIds.map((id) => [id, builder.practiceDesignStep.designs[id]?.revision]),
        ),
      }));
      builder.generateStep.startLectureGeneration(waitingLectureIds);
    },
  });
  const allGoalsApproved = builder.generateStep.allGoalsApproved;
  const wasApproved = useRef(allGoalsApproved);
  useEffect(() => {
    // After the last goal approval, continue to drafts; later visits to the plan stay put.
    if (allGoalsApproved && !wasApproved.current && builder.activeStep === "design") {
      builder.setActiveStep("generate");
    }
    wasApproved.current = allGoalsApproved;
  }, [allGoalsApproved, builder]);
  const reviewLectureIds = builder.generateStep.previewLectures.map((lecture) => lecture.id);
  const learningDesign = useProfessorLearningDesignReviews({
    courseId: builder.workspace?.courseId ?? null,
    lectureIds: reviewLectureIds,
    revisionKey: JSON.stringify([builder.draftRestoreRevision, builder.generateStep.canvas]),
    session: props.session,
  });
  useVersionUpdateActivity(
    builder.isRestoring ||
      builder.uploadStep.pendingAction !== null ||
      builder.uploadStep.uploadFiles.length > 0,
  );

  const stage = builderStage(builder.activeStep);
  // "Approve & publish" covers reviewed drafts that are not live and not regenerating.
  const publishableIds = reviewLectureIds.filter(
    (id) =>
      learningDesign.reviews[id] &&
      !builder.publishStep.lectures.some((lecture) => lecture.id === id && lecture.published) &&
      !builder.generateStep.retryingLectureIds.has(id) &&
      (builder.generateStep.generationProgress.find((item) => item.lectureId === id)?.status ??
        "ready") === "ready",
  );
  const canPublish =
    builder.publishStep.canPublish && !learningDesign.saving && publishableIds.length > 0;
  const approveAndPublish = async (ids: readonly string[]) => {
    builder.generateStep.onContinueToPublish();
    // Each approval binds the exact draft revisions the professor is looking at.
    await builder.publishStep.onPublish(
      ids.map((lectureId) => ({
        lectureId,
        approval: learningDesignApprovalInput(learningDesign.reviews[lectureId]),
      })),
    );
    await Promise.all(ids.map((id) => learningDesign.reload(id)));
  };
  const draft = (
    <ProfessorCanvasDraftStep
      publicationAction={
        builder.generateStep.canvas ? (
          <ProfessorPublishStep
            {...builder.publishStep}
            canPublish={canPublish}
            publishableCount={publishableIds.length}
            onPublish={() => {
              if (canPublish) void approveAndPublish(publishableIds);
            }}
          />
        ) : null
      }
      {...builder.generateStep}
      onReviewLearningGoals={() => builder.setActiveStep("design")}
      lectures={builder.publishStep.lectures}
      renderPublishedLecture={(lectureId) =>
        builder.workspace ? (
          <ProfessorLanguageVariants
            courseId={builder.workspace.courseId}
            lectureId={lectureId}
            session={props.session}
          />
        ) : null
      }
      renderImplementationChanges={(lectureId) =>
        builder.workspace ? (
          <ProfessorImplementationChanges
            key={lectureId}
            courseId={builder.workspace.courseId}
            lectureId={lectureId}
            session={props.session}
          />
        ) : null
      }
      learningDesignReviews={learningDesign.reviews}
      learningDesignErrors={learningDesign.errorsByLecture}
      onReloadLearningDesign={(id) => void learningDesign.reload(id)}
      learningDesignSaving={learningDesign.saving}
      onApproveLearningDesign={(lectureId) => void approveAndPublish([lectureId])}
      onSaveLearningDesign={(lectureId, update) => void learningDesign.save(lectureId, update)}
    />
  );
  return (
    <main className="professor-screen">
      <section className="builder-masthead" data-tour="course-creation-workflow">
        <div>
          <h1>{t(`builder.journey.${stage}`)}</h1>
          <p>{builderStageDescription(stage, t)}</p>
        </div>
        <div className="professor-header-actions">
          {builder.workspace && builder.courseTitle ? (
            <>
              <p className="builder-current-course">
                {t("builder.resume.current", { course: builder.courseTitle })}
              </p>
              <button
                className="refresh-button"
                disabled={builder.isRestoring || builder.uploadStep.pendingAction !== null}
                type="button"
                onClick={builder.startNewCourse}
              >
                {t("builder.resume.startNew")}
              </button>
            </>
          ) : null}
          <button
            className="refresh-button"
            disabled={
              !builder.workspace || builder.isRestoring || builder.uploadStep.pendingAction !== null
            }
            type="button"
            onClick={builder.restoreWorkspace}
          >
            {builder.isRestoring ? t("professor.refreshing") : t("professor.refreshWorkspace")}
          </button>
        </div>
      </section>
      <div className="builder-layout">
        <ProfessorBuilderStepper
          activeStep={builder.activeStep}
          steps={builder.steps}
          onStepChange={builder.setActiveStep}
        />
        <div className="builder-workspace">
          <div className="professor-flow">
            {builder.activeStep === "define" ? (
              <ProfessorCourseSetupStep {...builder.defineStep} />
            ) : null}
            {stage === "materials" ? <ProfessorBuilderMaterials builder={builder} /> : null}
            {stage === "media" ? <ProfessorReviewStep {...builder.mediaStep} /> : null}
            {builder.activeStep === "design" ? (
              <ProfessorPracticeDesignStep {...builder.practiceDesignStep} />
            ) : null}
            {stage === "release" ? <>{draft}</> : null}
          </div>
          {stage === "materials" ? (
            <ProfessorGenerationWarnings warnings={builder.generationWarnings} />
          ) : null}
          {builder.notice ? <p className="form-success">{builder.notice}</p> : null}
          {builder.error ? <p className="form-error">{builder.error}</p> : null}
          {learningDesign.error ? <p className="form-error">{learningDesign.error}</p> : null}
        </div>
      </div>
    </main>
  );
}

function builderStageDescription(stage: BuilderStage, t: ReturnType<typeof useI18n>["t"]) {
  if (stage === "course") return t("builder.stage.define");
  if (stage === "materials") return t("builder.stage.upload");
  if (stage === "media") return t("builder.stage.review");
  if (stage === "plan") return t("builder.stage.design");
  return t("builder.stage.generate");
}
