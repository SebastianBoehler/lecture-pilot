import { useI18n } from "./i18n";
import {
  builderStepLabel,
  type BuilderStep,
  ProfessorBuilderStepper,
} from "./ProfessorBuilderStepper";
import { ProfessorCanvasDraftStep } from "./ProfessorCanvasDraftStep";
import { ProfessorCourseSetupStep } from "./ProfessorCourseSetupStep";
import { ProfessorGenerationWarnings } from "./ProfessorGenerationWarnings";
import { ProfessorMaterialStep } from "./ProfessorMaterialStep";
import { ProfessorPublishStep } from "./ProfessorPublishStep";
import { ProfessorReviewStep } from "./ProfessorReviewStep";
import {
  useProfessorCourseBuilder,
  type ProfessorCourseBuilderProps,
} from "./useProfessorCourseBuilder";
import { useVersionUpdateActivity } from "./VersionUpdateBoundary";

export function ProfessorCourseBuilder(props: ProfessorCourseBuilderProps) {
  const { t } = useI18n();
  const builder = useProfessorCourseBuilder(props);
  useVersionUpdateActivity(
    builder.isRestoring ||
      builder.uploadStep.pendingAction !== null ||
      builder.uploadStep.uploadFiles.length > 0,
  );

  return (
    <main className="professor-screen">
      <section className="builder-masthead">
        <div>
          <h1>{builderStepLabel(builder.activeStep, t)}</h1>
          <p>{builderStageDescription(builder.activeStep, t)}</p>
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
            {builder.activeStep === "upload" ? (
              <ProfessorMaterialStep {...builder.uploadStep} />
            ) : null}
            {builder.activeStep === "review" ? (
              <ProfessorReviewStep {...builder.mediaStep} />
            ) : null}
            {builder.activeStep === "generate" ? (
              <ProfessorCanvasDraftStep {...builder.generateStep} />
            ) : null}
            {builder.activeStep === "publish" ? (
              <ProfessorPublishStep {...builder.publishStep} />
            ) : null}
          </div>
          <ProfessorGenerationWarnings warnings={builder.generationWarnings} />
          {builder.notice ? <p className="form-success">{builder.notice}</p> : null}
          {builder.error ? <p className="form-error">{builder.error}</p> : null}
        </div>
      </div>
    </main>
  );
}

function builderStageDescription(step: BuilderStep, t: ReturnType<typeof useI18n>["t"]) {
  if (step === "define") return t("builder.stage.define");
  if (step === "upload") return t("builder.stage.upload");
  if (step === "review") return t("builder.stage.review");
  if (step === "generate") return t("builder.stage.generate");
  return t("builder.stage.publish");
}
