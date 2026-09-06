import { ProfessorImplementationChanges } from "./ProfessorImplementationChanges";
import { useI18n } from "./i18n";
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
import { useProfessorLearningDesignReviews } from "./useProfessorLearningDesignReviews";
import { useVersionUpdateActivity } from "./VersionUpdateBoundary";

export function ProfessorCourseBuilder(props: ProfessorCourseBuilderProps) {
  const { t } = useI18n();
  const builder = useProfessorCourseBuilder(props);
  const reviewLectureIds = builder.generateStep.previewLectures.map((lecture) => lecture.id);
  const learningDesign = useProfessorLearningDesignReviews({
    courseId: builder.workspace?.courseId ?? null,
    lectureIds: reviewLectureIds,
    revisionKey: JSON.stringify([
      builder.generateStep.canvas,
      builder.generateStep.generationProgress,
    ]),
    session: props.session,
  });
  useVersionUpdateActivity(
    builder.isRestoring ||
      builder.uploadStep.pendingAction !== null ||
      builder.uploadStep.uploadFiles.length > 0,
  );

  const stage = builderStage(builder.activeStep);
  const canPublish =
    builder.publishStep.canPublish &&
    !learningDesign.saving &&
    learningDesign.allApproved &&
    reviewLectureIds.length > 0 &&
    !builder.generateStep.isGenerating &&
    builder.generateStep.retryingLectureIds.size === 0 &&
    builder.generateStep.generationProgress.every((item) => item.status === "ready");
  const draft = (
    <ProfessorCanvasDraftStep
      {...builder.generateStep}
      learningDesignReviews={learningDesign.reviews}
      learningDesignSaving={learningDesign.saving}
      onApproveLearningDesign={(lectureId) => void learningDesign.approve(lectureId)}
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
          <button
            className="refresh-button"
            disabled={!builder.workspace || builder.isRestoring}
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
            {builder.activeStep === "design" ? (
              <ProfessorPracticeDesignStep {...builder.practiceDesignStep} />
            ) : null}
            {stage === "release" ? (
              <>
                {builder.publishStep.ready ? (
                  <details className="builder-optional">
                    <summary>{t("builder.release.revision")}</summary>
                    {draft}
                  </details>
                ) : (
                  draft
                )}
                {builder.generateStep.canvas ? (
                  <ProfessorPublishStep
                    {...builder.publishStep}
                    courseId={builder.workspace?.courseId}
                    session={props.session}
                    canPublish={canPublish}
                    onPublish={() => {
                      if (!canPublish) return;
                      builder.generateStep.onContinueToPublish();
                      void builder.publishStep.onPublish();
                    }}
                  />
                ) : null}
              </>
            ) : null}
          </div>
          {stage === "release" && builder.workspace
            ? reviewLectureIds.map((lectureId) => (
                <ProfessorImplementationChanges
                  key={lectureId}
                  courseId={builder.workspace!.courseId}
                  lectureId={lectureId}
                  session={props.session}
                />
              ))
            : null}
          <ProfessorGenerationWarnings warnings={builder.generationWarnings} />
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
  if (stage === "plan") return t("builder.stage.design");
  return t("builder.stage.generate");
}
