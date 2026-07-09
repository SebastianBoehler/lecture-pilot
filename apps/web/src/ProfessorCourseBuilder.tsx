import { useI18n } from "./i18n";
import { ProfessorBuilderStepper } from "./ProfessorBuilderStepper";
import { ProfessorCanvasDraftStep } from "./ProfessorCanvasDraftStep";
import { CourseSetupStep } from "./ProfessorCourseBuilderParts";
import { ProfessorGenerationWarnings } from "./ProfessorGenerationWarnings";
import { ProfessorMaterialStep } from "./ProfessorMaterialStep";
import { ProfessorPublishStep } from "./ProfessorPublishStep";
import { ProfessorReviewStep } from "./ProfessorReviewStep";
import {
  useProfessorCourseBuilder,
  type ProfessorCourseBuilderProps,
} from "./useProfessorCourseBuilder";

export function ProfessorCourseBuilder(props: ProfessorCourseBuilderProps) {
  const { t } = useI18n();
  const builder = useProfessorCourseBuilder(props);

  return (
    <main className="professor-screen">
      <section className="professor-page-header">
        <div>
          <h1>{t("professor.builder.title")}</h1>
          <p>{t("professor.builder.subtitle")}</p>
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
      <ProfessorBuilderStepper
        activeStep={builder.activeStep}
        steps={builder.steps}
        onStepChange={builder.setActiveStep}
      />
      <div className="professor-flow">
        {builder.activeStep === "define" ? <CourseSetupStep {...builder.defineStep} /> : null}
        {builder.activeStep === "upload" ? <ProfessorMaterialStep {...builder.uploadStep} /> : null}
        {builder.activeStep === "review" ? <ProfessorReviewStep {...builder.mediaStep} /> : null}
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
    </main>
  );
}
